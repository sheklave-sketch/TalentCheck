"""Help and cancel handlers."""
from telegram import Update
from telegram.ext import ContextTypes
from .. import messages


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(messages.HELP_TEXT)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel — clear all active conversation flows."""
    # Clear all flow states
    for key in list(context.user_data.keys()):
        if key.startswith(("reg_", "demo_", "invite_", "session", "practice",
                           "pending_payment", "q_start_time", "chat_id")):
            context.user_data.pop(key, None)

    await update.message.reply_text(messages.CANCEL_MESSAGE)
