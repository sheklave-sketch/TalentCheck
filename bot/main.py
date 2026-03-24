"""TalentCheck Telegram Bot — Entry point."""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)
from .config import BOT_TOKEN
from .handlers.start import start_command
from .handlers.assessment import (
    begin_assessment_callback,
    answer_callback,
    next_section_callback,
    cancel_assessment_callback,
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


def main():
    if not BOT_TOKEN:
        logger.error("TC_BOT_TOKEN not set in .env")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # ─── Commands ──────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("practice", practice_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # ─── Assessment callbacks ──────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(begin_assessment_callback, pattern=r"^begin\|"))
    app.add_handler(CallbackQueryHandler(answer_callback, pattern=r"^ans\|"))
    app.add_handler(CallbackQueryHandler(next_section_callback, pattern=r"^next_section\|"))
    app.add_handler(CallbackQueryHandler(cancel_assessment_callback, pattern=r"^cancel_assessment$"))

    # ─── Practice callbacks ────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(practice_category_callback, pattern=r"^practice\|"))
    app.add_handler(CallbackQueryHandler(practice_answer_callback, pattern=r"^pans\|"))
    app.add_handler(CallbackQueryHandler(practice_again_callback, pattern=r"^practice_again$"))
    app.add_handler(CallbackQueryHandler(practice_done_callback, pattern=r"^practice_done$"))

    logger.info("TalentCheck bot starting (polling)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
