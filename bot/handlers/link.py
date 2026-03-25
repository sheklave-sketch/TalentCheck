"""HR account linking via one-time code."""
import secrets
from telegram import Update
from telegram.ext import ContextTypes
from ..api_client import api_post


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a link code for HR to connect their Telegram to their web account."""
    telegram_id = update.effective_user.id
    code = f"TC-{secrets.token_hex(3).upper()}"

    # Save the code via API
    result = await api_post("/link-hr", {
        "telegram_id": telegram_id,
        "link_code": code,
    })

    if isinstance(result, dict) and result.get("error"):
        # If no pending link exists, create a general instruction
        await update.message.reply_text(
            "Link your Telegram to your TalentCheck account:\n\n"
            f"Your code: {code}\n\n"
            "Steps:\n"
            "1. Log in to talentcheck-tau.vercel.app\n"
            "2. Go to Settings > Integrations\n"
            "3. Enter this code\n\n"
            "Code expires in 10 minutes."
        )
    else:
        await update.message.reply_text(
            "Link your Telegram to your TalentCheck account:\n\n"
            f"Your code: {code}\n\n"
            "Go to Settings > Integrations on the web dashboard\n"
            "and enter this code.\n\n"
            "Code expires in 10 minutes."
        )

    context.user_data["link_code"] = code
    context.user_data["link_telegram_id"] = telegram_id
