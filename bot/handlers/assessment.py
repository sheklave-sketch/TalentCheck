"""Full assessment flow via inline keyboards."""
import time
import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..api_client import api_post
from ..keyboards import answer_keyboard, continue_section_keyboard, candidate_menu_keyboard
from ..timer import format_time, schedule_deadline, cancel_deadline
from .. import messages

logger = logging.getLogger(__name__)


def _sid_short(session_id: str) -> str:
    """Shorten session ID for callback data (64-byte limit)."""
    return session_id[:8]


async def _send_question(
    update_or_msg,
    context: ContextTypes.DEFAULT_TYPE,
    session_data: dict,
):
    """Send the current question to the user."""
    tests = session_data["tests"]
    ti = session_data["current_test_index"]
    qi = session_data["current_question_index"]
    session_id = session_data["session_id"]
    remaining = session_data.get("seconds_remaining", 0)

    test = tests[ti]
    question = test["questions"][qi]
    total_q = len(test["questions"])
    test_label = test["test_key"].replace("_", " ").title()

    text = messages.QUESTION_TEMPLATE.format(
        test_label=test_label,
        q_num=qi + 1,
        q_total=total_q,
        time_remaining=format_time(remaining),
        question_text=question["text"],
    )

    kb = answer_keyboard(_sid_short(session_id), question["id"], question["options"])

    # Try to edit existing message, else send new
    if hasattr(update_or_msg, "edit_message_text"):
        try:
            await update_or_msg.edit_message_text(text=text, reply_markup=kb)
            return
        except Exception:
            pass

    chat_id = context.user_data.get("chat_id")
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)


async def begin_assessment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Start Assessment' button press."""
    query = update.callback_query
    await query.answer()

    data = query.data  # begin|{invite_token}
    _, invite_token = data.split("|", 1)

    telegram_id = query.from_user.id
    context.user_data["chat_id"] = query.message.chat_id

    result = await api_post("/start-session", {
        "invite_token": invite_token,
        "telegram_id": telegram_id,
    })

    if result.get("error"):
        await query.edit_message_text(f"Error: {result.get('detail', 'Could not start session')}")
        return

    # Store session data
    context.user_data["session"] = {
        "session_id": result["session_id"],
        "bot_session_id": result["bot_session_id"],
        "tests": result["tests"],
        "current_test_index": result["current_test_index"],
        "current_question_index": result["current_question_index"],
        "seconds_remaining": result["seconds_remaining"],
        "invite_token": invite_token,
    }
    context.user_data["q_start_time"] = time.time()

    # Schedule auto-submit at deadline
    schedule_deadline(
        context,
        session_id=result["session_id"],
        bot_session_id=result["bot_session_id"],
        chat_id=query.message.chat_id,
        seconds=result["seconds_remaining"],
    )

    await _send_question(query, context, context.user_data["session"])


async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle A/B/C/D answer button press."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")  # ans|{sid_short}|{question_id}|{answer_key}
    if len(parts) != 4:
        return

    _, sid_short, question_id, answer_key = parts
    session_data = context.user_data.get("session")
    if not session_data:
        await query.edit_message_text("Session expired. Please use your invite link again.")
        return

    # Calculate time taken for this question
    q_start = context.user_data.get("q_start_time", time.time())
    time_taken = int(time.time() - q_start)

    ti = session_data["current_test_index"]
    test = session_data["tests"][ti]

    # Submit answer to API
    result = await api_post("/submit-answer", {
        "session_id": session_data["session_id"],
        "bot_session_id": session_data["bot_session_id"],
        "test_key": test["test_key"],
        "question_id": question_id,
        "answer": answer_key,
        "time_taken_seconds": time_taken,
    })

    if result.get("error"):
        if "expired" in str(result.get("detail", "")).lower():
            await query.edit_message_text(messages.TIME_EXPIRED)
            context.user_data.pop("session", None)
            return
        await query.edit_message_text(f"Error: {result.get('detail')}")
        return

    session_data["seconds_remaining"] = result.get("seconds_remaining", 0)

    # Advance to next question
    qi = session_data["current_question_index"] + 1
    total_q = len(test["questions"])

    if qi < total_q:
        # Next question in same test section
        session_data["current_question_index"] = qi
        context.user_data["q_start_time"] = time.time()

        # Update progress on server (fire and forget)
        await api_post("/update-progress", {
            "bot_session_id": session_data["bot_session_id"],
            "current_test_index": ti,
            "current_question_index": qi,
        })

        await _send_question(query, context, session_data)
    else:
        # Test section complete — check if more sections
        next_ti = ti + 1
        if next_ti < len(session_data["tests"]):
            # More sections remaining
            session_data["current_test_index"] = next_ti
            session_data["current_question_index"] = 0
            context.user_data["q_start_time"] = time.time()

            await api_post("/update-progress", {
                "bot_session_id": session_data["bot_session_id"],
                "current_test_index": next_ti,
                "current_question_index": 0,
            })

            next_test = session_data["tests"][next_ti]
            next_label = next_test["test_key"].replace("_", " ").title()
            test_label = test["test_key"].replace("_", " ").title()
            remaining = format_time(session_data["seconds_remaining"])

            await query.edit_message_text(
                messages.SECTION_COMPLETE.format(
                    test_label=test_label,
                    next_label=next_label,
                    time_remaining=remaining,
                ),
                reply_markup=continue_section_keyboard(_sid_short(session_data["session_id"])),
            )
        else:
            # All tests done — submit
            await _finalize_session(query, context, session_data)


async def next_section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Continue' button between test sections."""
    query = update.callback_query
    await query.answer()

    session_data = context.user_data.get("session")
    if not session_data:
        await query.edit_message_text("Session expired.")
        return

    context.user_data["q_start_time"] = time.time()
    await _send_question(query, context, session_data)


async def _finalize_session(query, context, session_data):
    """Submit the session and show completion message."""
    # Cancel the auto-submit deadline job
    cancel_deadline(context, session_data["session_id"])

    result = await api_post("/submit-session", {
        "session_id": session_data["session_id"],
        "bot_session_id": session_data["bot_session_id"],
    })

    context.user_data.pop("session", None)

    await query.edit_message_text(
        messages.ASSESSMENT_COMPLETE,
        reply_markup=candidate_menu_keyboard(),
    )


async def cancel_assessment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel button during assessment."""
    query = update.callback_query
    await query.answer()

    session_data = context.user_data.get("session")
    if session_data:
        cancel_deadline(context, session_data["session_id"])

    context.user_data.pop("session", None)
    await query.edit_message_text(
        "Assessment cancelled. You can use your invite link again to start.",
        reply_markup=candidate_menu_keyboard(),
    )
