"""HR account linking via one-time code."""
import secrets
from telegram import Update
from telegram.ext import ContextTypes
from ..api_client import api_post


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a link code for HR to connect their Telegram."""
    code = f"TC-{secrets.token_hex(3).upper()}"

    await update.message.reply_text(
        "Link your Telegram to your TalentCheck account:\n\n"
        f"🔑 Your code: {code}\n\n"
        "Go to Settings > Integrations on the web dashboard\n"
        "and enter this code.\n\n"
        "Code expires in 10 minutes."
    )

    # Store code with telegram_id for the web dashboard to match
    context.user_data["link_code"] = code
    context.user_data["link_telegram_id"] = update.effective_user.id
