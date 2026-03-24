"""Handle /start and deep links."""
from telegram import Update
from telegram.ext import ContextTypes
from ..api_client import api_get
from ..keyboards import start_assessment_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start and /start {invite_token}."""
    args = context.args

    # Deep link: /start {invite_token}
    if args and len(args) == 1:
        invite_token = args[0]
        try:
            data = await api_get(f"/candidate-by-token/{invite_token}")
        except Exception:
            await update.message.reply_text("Invalid or expired invite link.")
            return

        if isinstance(data, dict) and data.get("error"):
            await update.message.reply_text(f"Error: {data.get('detail', 'Unknown error')}")
            return

        tests_list = "\n".join(
            f"  • {t['test_key'].replace('_', ' ').title()} ({t['time_limit_minutes']} min)"
            for t in data["test_config"]
        )

        msg = (
            f"Welcome to TalentCheck, {data['candidate_name']}!\n\n"
            f"{data['org_name']} has invited you to complete:\n"
            f"📋 {data['assessment_title']}\n\n"
            f"Tests included:\n{tests_list}\n\n"
            f"Total time: {data['total_time_limit_minutes']} minutes\n"
            f"Total questions: {data['total_questions']}\n\n"
            f"⚠️ Once you start, the timer begins and cannot be paused."
        )
        await update.message.reply_text(msg, reply_markup=start_assessment_keyboard(invite_token))
        return

    # Normal /start — welcome message
    await update.message.reply_text(
        "Welcome to TalentCheck Ethiopia!\n\n"
        "🧠 Hire by Skill, Not CV.\n\n"
        "Commands:\n"
        "/practice — Try free practice tests\n"
        "/help — Get help\n\n"
        "If you received an assessment invite link, tap it to begin."
    )
