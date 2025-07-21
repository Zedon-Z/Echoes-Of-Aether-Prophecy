# phases.py (converted for Application API)

import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from storage import database as db
from engine.roles import assign_roles
from engine.tasks import assign_task
from collections import Counter

twist_counter = {}
active_vote_buttons = {}
pending_powers = {}

def get_dawn_story():
    return random.choice([
        "Three bells rang. One for the fallen. One for the forgotten. The third? It rang before it should have.",
        "A letter arrived. No name, only the words: 'It wasn’t supposed to be you.'",
        "The child in the square pointed at you. Then vanished."
    ])

def get_night_story():
    return random.choice([
        "The wind screamed once. Someone screamed louder.",
        "In every mirror, someone different stared back.",
        "Shadows whispered your name. Will you answer?"
    ])

# -- Begin Game --
async def begin_game(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if not db.is_game_active(chat_id):
        await context.bot.send_message(chat_id, "⚠️ Game was cancelled or never started.")
        return
    if db.has_game_started(chat_id):
        await context.bot.send_message(chat_id, "⚠️ Game already started.")
        return
    players = db.get_player_list(chat_id)
    if len(players) < 3:
        await context.bot.send_message(chat_id, "❌ Not enough players to begin. Minimum 3 required.")
        return

    db.mark_game_started(chat_id)
    assign_roles(chat_id, players, context)

    await context.bot.send_animation(chat_id, animation='https://media.giphy.com/media/QBd2kLB5qDmysEXre9/giphy.gif')
    await context.bot.send_message(chat_id, "🎮 *The game begins! Night falls...*", parse_mode='Markdown')
    await start_night_phase(context, chat_id)

# -- Night Phase --
async def start_night_phase(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await context.bot.send_animation(chat_id, animation='https://media.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif')
    await context.bot.send_message(
        chat_id,
        text=f"🌙 *Night falls.*\n{get_night_story()}\nEach role must act in shadows.",
        parse_mode="Markdown"
    )

    db.set_phase(chat_id, "night")
    db.expire_effects(chat_id, phase="night")

    alive_players = db.get_alive_players(chat_id)
    usernames = {uid: db.get_username(uid) or f"user{uid}" for uid in alive_players}

    for user_id in alive_players:
        role = db.get_player_role(chat_id, user_id)
        if role in ["Goat"]:  # no power
            continue

        buttons = [
            [InlineKeyboardButton(f"Use Power on {usernames[target_id]}", callback_data=f"usepower_{target_id}")]
            for target_id in alive_players if target_id != user_id
        ]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🔮 Choose a target to use your power on:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            print(f"[WARN] Could not send power buttons to {user_id}: {e}")

    context.job_queue.run_once(lambda ctx: start_day_phase(ctx, chat_id), when=90)

# -- Day Phase --
async def start_day_phase(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    deaths = db.games[chat_id].pop("deaths", [])
    for uid in deaths:
        db.kill_player(chat_id, uid)
        await context.bot.send_message(chat_id, f"💀 @{db.get_username(uid)} was found dead at dawn ⚰️...")

    await context.bot.send_animation(chat_id, animation='https://media.giphy.com/media/3oEjHG3rG7HrzUpt7W/giphy.gif')
    await context.bot.send_message(
        chat_id,
        text=f"🌅 *Day Phase Begins.*\n{get_dawn_story()}\nThe sun rises. Whispers turn to accusations. Discuss and vote wisely.",
        parse_mode='Markdown'
    )

    db.increment_round(chat_id)
    if db.get_round(chat_id) >= 4:
        await start_final_echo(context, chat_id)

    maybe_trigger_plot_twist(chat_id, context)
    db.set_phase(chat_id, "day")
    db.reset_votes(chat_id)
    db.expire_effects(chat_id, phase="day")

    players = db.get_alive_players(chat_id)
    usernames = {uid: db.get_username(uid) or f"user{uid}" for uid in players}

    for user_id in players:
        vote_buttons = [
            [InlineKeyboardButton(f"Vote: {usernames[tid]}", callback_data=f"vote_{tid}")]
            for tid in players if tid != user_id
        ]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🗳️ *Vote privately:* Who should be eliminated?",
                reply_markup=InlineKeyboardMarkup(vote_buttons),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"[WARN] Could not send private vote buttons to {user_id}: {e}")

    for user_id in players:
        task_roll = random.choice(["phrase", "protect", "abstain"])
        if task_roll == "phrase":
            assign_task(user_id, "Say: The stars remember me.", "say_stars")
        elif task_roll == "protect":
            assign_task(user_id, "Keep another player alive for 3 rounds.", "guard_3rounds")
        elif task_roll == "abstain":
            assign_task(user_id, "Avoid voting for two days.", "no_vote2")
        try:
            await context.bot.send_message(user_id, "📜 A new task has been assigned.\nUse /mytasks to view it.")
        except Exception as e:
            print(f"[WARN] Task DM error to {user_id}: {e}")

    context.job_queue.run_once(lambda ctx: tally_votes(ctx, chat_id), when=90)

# -- Tally Votes --
async def tally_votes(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    votes = db.games[chat_id].get("votes", {})
    if not votes:
        await context.bot.send_message(chat_id, "❌ No votes recorded.")
        return

    tally = Counter()
    for voter_id in db.get_alive_players(chat_id):
        voted = voter_id in votes
        db.check_abstain(voter_id, voted)

    for voter_id, target_id in votes.items():
        db.notify_allies_vote(chat_id, voter_id, target_id, context)

    for voter, target in votes.items():
        if db.is_player_protected(target): continue
        if db.is_vote_disabled(chat_id, voter): continue
        tally[target] += 1

    if not tally:
        await context.bot.send_message(chat_id, "🛡️ All votes were blocked or invalid.")
        return

    target_id, count = tally.most_common(1)[0]
    db.kill_player(chat_id, target_id)
    await context.bot.send_message(chat_id, f"⚖️ @{db.get_username(target_id)} eliminated with {count} votes.")
    db.clear_votes(chat_id)
    db.auto_complete_tasks()

    # Check win
    from engine.win import check_for_winner
    winner = check_for_winner(chat_id)
    if winner:
        await context.bot.send_message(chat_id, f"🏆 *Victory:* {winner}", parse_mode="Markdown")

# -- Final Echo --
async def start_final_echo(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await context.bot.send_message(chat_id, "🌌 *The Core fractures. The Final Echo begins.*", parse_mode="Markdown")
    players = db.get_alive_players(chat_id)
    options = ["Save the Core", "Destroy the Core", "Escape the Core"]
    buttons = [[InlineKeyboardButton(opt, callback_data=f"echo_vote_{opt.lower().replace(' ', '_')}")] for opt in options]

    for uid in players:
        await context.bot.send_message(
            uid,
            "What will you choose?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# -- Plot Twist Handler --
def maybe_trigger_plot_twist(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    if db.get_round(chat_id) == 3:
        trigger_false_prophecy(chat_id, context)

    count = twist_counter.get(chat_id, 0) + 1
    twist_counter[chat_id] = count

    if count % 3 != 0:
        return

    twists = [
        "Echo Swap! Roles shuffled among players...",
        "Memory Wipe! All active tasks reset.",
        "False Prophet! Oracle visions are reversed.",
        "Emotional Collapse! Everyone loses 1 item.",
        "Night of Whispers... Votes next round are anonymous."
    ]
    twist = random.choice(twists)
    context.bot.send_message(chat_id, f"🌪 *Plot Twist!*\n{twist}", parse_mode='Markdown')

    if "Memory Wipe" in twist:
        for user_id in db.get_alive_players(chat_id):
            db.abandon_current_task(user_id)
    elif "Echo Swap" in twist:
        players = list(db.games[chat_id]["players"].keys())
        roles = [db.games[chat_id]["players"][pid]["role"] for pid in players]
        random.shuffle(roles)
        for pid, new_role in zip(players, roles):
            db.games[chat_id]["players"][pid]["role"] = new_role

def trigger_false_prophecy(chat_id, context):
    prophecy_lines = [
        "🌫️ *A False Vision descends...* The sky whispers lies.",
        "🪞 *Reality fractures...* Not all victories are as they seem.",
    ]
    context.bot.send_message(chat_id, random.choice(prophecy_lines), parse_mode="Markdown")
    db.games[chat_id]["false_prophecy"] = True
