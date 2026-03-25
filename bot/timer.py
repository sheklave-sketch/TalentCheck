"""JobQueue helpers for assessment deadlines and auto-submit."""
import logging
from telegram.ext import ContextTypes
from .api_client import api_post

logger = logging.getLogger(__name__)


def format_time(seconds: int) -> str:
    """Format seconds as MM:SS."""
    if seconds < 0:
        seconds = 0
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def schedule_deadline(context: ContextTypes.DEFAULT_TYPE, session_id: str,
                      bot_session_id: str, chat_id: int, seconds: int):
    """Schedule an auto-submit job when the deadline expires."""
    job_name = f"deadline_{session_id}"

    # Remove any existing deadline job for this session
    existing_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in existing_jobs:
        job.schedule_removal()

    context.job_queue.run_once(
        auto_submit_job,
        when=seconds,
        data={
            "session_id": session_id,
            "bot_session_id": bot_session_id,
            "chat_id": chat_id,
        },
        name=job_name,
    )
    logger.info(f"Scheduled deadline for session {session_id[:8]} in {seconds}s")


def cancel_deadline(context: ContextTypes.DEFAULT_TYPE, session_id: str):
    """Cancel the auto-submit deadline job for a session."""
    job_name = f"deadline_{session_id}"
    jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in jobs:
        job.schedule_removal()
    logger.info(f"Cancelled deadline for session {session_id[:8]}")


async def auto_submit_job(context: ContextTypes.DEFAULT_TYPE):
    """Auto-submit when server deadline expires. Called by JobQueue."""
    data = context.job.data
    session_id = data["session_id"]
    bot_session_id = data.get("bot_session_id")
    chat_id = data["chat_id"]

    logger.info(f"Auto-submitting session {session_id[:8]} due to timer expiry")

    # Submit the session
    await api_post("/submit-session", {
        "session_id": session_id,
        "bot_session_id": bot_session_id,
    })

    # Log the proctor event
    await api_post("/proctor-event", {
        "session_id": session_id,
        "type": "timer_expired",
        "detail": "Auto-submitted by bot due to timer expiry",
    })

    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Time's up! Your assessment has been auto-submitted.\n\n"
                "Thank you for using TalentCheck!"
            ),
        )
    except Exception as e:
        logger.error(f"Failed to notify user of auto-submit: {e}")
