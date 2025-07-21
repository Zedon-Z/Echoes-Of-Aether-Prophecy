# commands.py (converted for Application API)

import time
from functools import partial
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from storage import database as db
from engine import phases
from config import BOT_OWNER_ID
from storage import authorized
from engine.animation import dark_fantasy_animation

# ----- START -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *Echoes of Aether: The Silent War.*\n\n"
        "Use /startgame to begin a new game, or /join to join one.",
        parse_mode='Markdown'
    )

# ----- START GAME -----
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if db.is_game_active(chat_id):
        await update.message.reply_text("⚠️ A game is already running!")
        return

    db.start_new_game(chat_id)
    countdown = 60
    db.set_timer(chat_id, countdown)
    db.set_game_start_time(chat_id, int(time.time()) + countdown)

    # Schedule game to begin after countdown
    async def begin_game_callback(context: ContextTypes.DEFAULT_TYPE):
        await phases.begin_game(context, chat_id)

    context.job_queue.run_once(begin_game_callback, countdown)

    # Countdown alerts
    def countdown_alert(seconds_left):
        async def alert_fn(context: ContextTypes.DEFAULT_TYPE):
            emoji = "⏳" if seconds_left > 5 else "🚨"
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{emoji} *{seconds_left} seconds left before the game begins!*",
                parse_mode='Markdown'
            )
        return alert_fn

    if countdown >= 30:
        context.job_queue.run_once(countdown_alert(30), countdown - 30)
    if countdown >= 10:
        context.job_queue.run_once(countdown_alert(10), countdown - 10)
    if countdown >= 5:
        context.job_queue.run_once(countdown_alert(5), countdown - 5)

    # Join buttons
    join_btn = [[InlineKeyboardButton("🔹 Join Game", callback_data="join")]]
    await context.bot.send_message(
        chat_id=chat_id,
        text="🧩 *Echoes of Aether Begins!*\nClick below to join the match!",
        reply_markup=InlineKeyboardMarkup(join_btn),
        parse_mode='Markdown'
    )

    player_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📜 *Players Joined:*\n_(Waiting...)_",
        parse_mode='Markdown'
    )
    db.set_game_message(chat_id, player_msg.message_id)

# ----- JOIN GAME -----
async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if not db.is_game_active(chat_id):
        await update.message.reply_text("No game has been started yet.")
        return

    username = user.username or user.full_name or f"user{user.id}"
    success = db.add_player(chat_id, user.id, user.full_name)
    db.set_username(chat_id, user.id, username)

    if not success:
        await update.message.reply_text("ℹ️ You're already in the game.")
        return

    players = db.get_player_list(chat_id)
    player_text = "\n".join(f"- @{db.get_username(pid) or f'user{pid}'}" for pid in players)

    join_msg_id = db.get_game_message(chat_id)
    if join_msg_id:
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Join", callback_data="join")]])
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=join_msg_id,
                text=f"📜 Players Joined:\n{player_text}",
                reply_markup=markup
            )
        except Exception as e:
            print(f"[WARN] Could not update player list message: {e}")

# ----- EXTEND TIME -----
async def extend_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not db.is_game_active(chat_id):
        await update.message.reply_text("❌ No active game to extend time for.")
        return

    db.extend_timer(chat_id, 30)
    await update.message.reply_text("⏳ Extra time added! Waiting for more players...")

# ----- FLEE -----
async def flee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if not db.is_game_active(chat_id):
        await update.message.reply_text("❌ There's no game to flee from.")
        return

    if db.remove_player(chat_id, user.id):
        await update.message.reply_text(f"🚪 {user.full_name} has left the game.")
    else:
        await update.message.reply_text("You’re not part of the game.")

# ----- VOTE -----
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not db.is_game_active(chat_id):
        await update.message.reply_text("No game in progress.")
        return

    players = db.get_player_list(chat_id)
    if not players:
        await update.message.reply_text("No players found.")
        return

    buttons = [
        [InlineKeyboardButton(name, callback_data=f"vote_{pid}")]
        for pid, name in players.items()
    ]
    await update.message.reply_text("🔍 *Vote for a suspect:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')

# ----- FORCE START -----
async def force_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if db.has_game_started(chat_id):
        await update.message.reply_text("⚠️ The game has already started.")
        return
    if not db.is_game_active(chat_id):
        await update.message.reply_text("❌ No game to start.")
        return

    players = db.get_player_list(chat_id)
    if len(players) < 3:
        await update.message.reply_text("⚠️ At least 3 players are needed to start the game.")
        return

    await update.message.reply_text("🚀 Forcing game start...")
    await phases.begin_game(context, chat_id)

# ----- CHAT ID -----
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: `{update.effective_chat.id}`", parse_mode='Markdown')

# ----- AUTHORIZE GROUP -----
async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text("🚫 You are not authorized to do this.")
        return

    chat_id = update.effective_chat.id
    if authorized.add_group(chat_id):
        await update.message.reply_text(f"✅ This group ({chat_id}) is now authorized.")
    else:
        await update.message.reply_text("ℹ️ This group is already authorized.")

# ----- DEAUTHORIZE GROUP -----
async def deauthorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text("🚫 You are not authorized to do this.")
        return

    chat_id = update.effective_chat.id
    if authorized.remove_group(chat_id):
        await update.message.reply_text(f"❌ This group ({chat_id}) has been removed from authorized list.")
    else:
        await update.message.reply_text("ℹ️ This group wasn't authorized.")

# ----- CANCEL GAME -----
async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not db.is_game_active(chat_id):
        await update.message.reply_text("❌ There’s no active game to cancel.")
        return

    db.cancel_game(chat_id)

    await update.message.reply_text("🚫 *The game has been cancelled.* Watch closely...", parse_mode='Markdown')

    try:
        await dark_fantasy_animation(context.bot, chat_id)
    except Exception as e:
        print(f"[WARN] Failed to run animation: {e}")
