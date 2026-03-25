"""TalentCheck Telegram Bot — Entry point with all handler registration."""
import logging
from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from .config import BOT_TOKEN
from . import messages
from .keyboards import fallback_keyboard

# Import handlers
from .handlers.start import (
    start_command,
    menu_command,
    role_callback,
    menu_callback,
    employer_menu_callback,
)
from .handlers.candidate import (
    registration_message_handler,
    candidate_reg_confirm_callback,
    test_detail_callback,
    pay_callback,
    verify_payment_callback,
    certificate_callback,
    results_command,
    browse_command,
)
from .handlers.assessment import (
    begin_assessment_callback,
    answer_callback,
    next_section_callback,
    cancel_assessment_callback,
)
from .handlers.employer import (
    employer_reg_confirm_callback,
    demo_command,
    demo_message_handler,
    demo_confirm_callback,
    invite_command,
    invite_message_handler,
    employer_results_command,
    employer_result_detail_callback,
)
from .handlers.practice import (
    practice_command,
    practice_category_callback,
    practice_answer_callback,
    practice_again_callback,
    practice_done_callback,
)
from .handlers.link import link_command
from .handlers.help import help_command, cancel_command

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application):
    """Set bot commands visible in Telegram's menu button."""
    commands = [
        BotCommand("start", "Welcome & main menu"),
        BotCommand("menu", "Open main menu"),
        BotCommand("practice", "Free practice tests"),
        BotCommand("browse", "Browse available tests"),
        BotCommand("results", "View your test results"),
        BotCommand("help", "Help & commands"),
        BotCommand("cancel", "Cancel current operation"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")


async def text_message_router(update, context):
    """Route text messages to the correct conversation handler based on user_data state."""
    # Check registration flow first
    if context.user_data.get("reg_flow"):
        handled = await registration_message_handler(update, context)
        if handled:
            return

    # Check demo request flow
    if context.user_data.get("demo_flow"):
        handled = await demo_message_handler(update, context)
        if handled:
            return

    # Check invite flow
    if context.user_data.get("invite_flow"):
        handled = await invite_message_handler(update, context)
        if handled:
            return

    # No active flow — show helpful fallback
    await update.message.reply_text(
        messages.UNKNOWN_INPUT,
        reply_markup=fallback_keyboard(),
    )


def main():
    if not BOT_TOKEN:
        logger.error("TC_BOT_TOKEN not set — cannot start bot")
        return

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # ─── Commands ────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("practice", practice_command))
    app.add_handler(CommandHandler("browse", browse_command))
    app.add_handler(CommandHandler("results", results_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("demo", demo_command))
    app.add_handler(CommandHandler("invite", invite_command))
    app.add_handler(CommandHandler("employer_results", employer_results_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # ─── Role selection ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(role_callback, pattern=r"^role\|"))

    # ─── Candidate menu ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu\|"))

    # ─── Employer menu ───────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(employer_menu_callback, pattern=r"^emenu\|"))

    # ─── Registration confirmations ──────────────────────────────────────
    app.add_handler(CallbackQueryHandler(candidate_reg_confirm_callback, pattern=r"^creg\|"))
    app.add_handler(CallbackQueryHandler(employer_reg_confirm_callback, pattern=r"^ereg\|"))

    # ─── Demo confirmation ───────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(demo_confirm_callback, pattern=r"^demo\|"))

    # ─── Test browsing ───────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(test_detail_callback, pattern=r"^test_detail\|"))

    # ─── Payment ─────────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(pay_callback, pattern=r"^pay\|"))
    app.add_handler(CallbackQueryHandler(verify_payment_callback, pattern=r"^verify_pay\|"))

    # ─── Assessment flow ─────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(begin_assessment_callback, pattern=r"^begin\|"))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern=r"^ans\|"))
    app.add_handler(CallbackQueryHandler(next_section_callback, pattern=r"^next_section\|"))
    app.add_handler(CallbackQueryHandler(cancel_assessment_callback, pattern=r"^cancel_assessment$"))

    # ─── Results & certificate ───────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(certificate_callback, pattern=r"^cert\|"))
    app.add_handler(CallbackQueryHandler(employer_result_detail_callback, pattern=r"^emp_result\|"))

    # ─── Practice flow ───────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(practice_category_callback, pattern=r"^practice\|"))
    app.add_handler(CallbackQueryHandler(practice_answer_callback, pattern=r"^pans\|"))
    app.add_handler(CallbackQueryHandler(practice_again_callback, pattern=r"^practice_again$"))
    app.add_handler(CallbackQueryHandler(practice_done_callback, pattern=r"^practice_done$"))

    # ─── Text message router (must be last) ──────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_router))

    logger.info("TalentCheck bot starting (long-polling)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
