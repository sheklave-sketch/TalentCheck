"""HR account linking via one-time code."""
import secrets
from telegram import Update
from telegram.ext import ContextTypes
from ..api_client import api_post
from .. import messages
from ..keyboards import back_to_menu_keyboard


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a link code for HR to connect their Telegram to their web account."""
    telegram_id = update.effective_user.id
    code = f"TC-{secrets.token_hex(3).upper()}"

    # Save the code via API
    result = await api_post("/link-hr", {
        "telegram_id": telegram_id,
        "link_code": code,
    })

    await update.message.reply_text(
        messages.LINK_SUCCESS.format(code=code),
        reply_markup=back_to_menu_keyboard(),
    )

    context.user_data["link_code"] = code
    context.user_data["link_telegram_id"] = telegram_id
