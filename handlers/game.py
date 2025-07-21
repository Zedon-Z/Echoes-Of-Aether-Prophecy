# game.py (converted for Application API)

from telegram import Update
from telegram.ext import ContextTypes
from engine import phases
from storage import database as db

# PHASE HANDLER: cycles day → night → dawn → day...
async def phase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not db.is_game_active(chat_id):
        await update.message.reply_text("No game is active right now.")
        return

    current_phase = db.get_phase(chat_id)

    if current_phase == "day":
        db.set_phase(chat_id, "night")
        story = phases.get_night_story()

        await update.message.reply_text(
            f"🌙 *Night Falls...*\n_{story}_",
            parse_mode="Markdown"
        )

        # ✅ Placeholder: trigger night logic — powers, tasks, deaths
        await phases.handle_night_phase(context, chat_id)

    elif current_phase == "night":
        db.set_phase(chat_id, "dawn")
        story = phases.get_dawn_story()

        await update.message.reply_text(
            f"🌅 *Dawn Breaks...*\n_{story}_",
            parse_mode="Markdown"
        )

        # ✅ Placeholder: reveal deaths, resolve night events
        await phases.handle_dawn_phase(context, chat_id)

    elif current_phase == "dawn":
        db.set_phase(chat_id, "day")
        await update.message.reply_text(
            "🌞 *A new day begins. Discussion resumes.*",
            parse_mode="Markdown"
        )

        # ✅ Placeholder: reset vote counts, assign tasks
        await phases.handle_day_phase(context, chat_id)

    else:
        db.set_phase(chat_id, "day")
        await update.message.reply_text("🔄 Starting Day Phase...", parse_mode="Markdown")


# GROUP MESSAGE LOGGER: for phrase-based task tracking
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    text = update.message.text

    # ✅ Log for phrase-completion task triggers
    db.record_message(user.id, text)
