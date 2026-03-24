"""Help and cancel handlers."""
from telegram import Update
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "TalentCheck Bot — Help\n\n"
        "Commands:\n"
        "/start — Welcome message\n"
        "/practice — Free practice tests (5 questions, with answers)\n"
        "/link — Link your Telegram to your HR account\n"
        "/help — This help message\n\n"
        "If you received an assessment invite link, tap it to start your test.\n\n"
        "Questions? Contact your HR team or visit talentcheck-tau.vercel.app"
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("session", None)
    context.user_data.pop("practice", None)
    await update.message.reply_text("Operation cancelled.")
