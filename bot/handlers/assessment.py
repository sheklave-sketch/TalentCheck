"""Full assessment flow via inline keyboards."""
import time
from telegram import Update
from telegram.ext import ContextTypes
from ..api_client import api_post
from ..keyboards import answer_keyboard, continue_section_keyboard


def _format_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def _sid_short(session_id: str) -> str:
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

    text = (
        f"📝 {test_label} — Question {qi + 1}/{total_q}\n"
        f"⏱ {_format_time(remaining)} remaining\n\n"
        f"{question['text']}"
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

    # Schedule auto-submit
    context.job_queue.run_once(
        _auto_submit_job,
        when=result["seconds_remaining"],
        data={"session_id": result["session_id"], "bot_session_id": result["bot_session_id"], "chat_id": query.message.chat_id},
        name=f"deadline_{result['session_id']}",
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

    # Calculate time taken
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
            await query.edit_message_text("⏱ Time's up! Your assessment has been auto-submitted.")
            return
        await query.edit_message_text(f"Error: {result.get('detail')}")
        return

    session_data["seconds_remaining"] = result.get("seconds_remaining", 0)

    # Advance to next question
    qi = session_data["current_question_index"] + 1
    total_q = len(test["questions"])

    if qi < total_q:
        # Next question in same test
        session_data["current_question_index"] = qi
        context.user_data["q_start_time"] = time.time()

        # Update progress on server
        await api_post("/update-progress", {
            "bot_session_id": session_data["bot_session_id"],
            "current_test_index": ti,
            "current_question_index": qi,
        })

        await _send_question(query, context, session_data)
    else:
        # Test section complete
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
            test_label = next_test["test_key"].replace("_", " ").title()
            remaining = _format_time(session_data["seconds_remaining"])

            await query.edit_message_text(
                f"✅ {test['test_key'].replace('_', ' ').title()} — Complete!\n\n"
                f"Next: {test_label}\n"
                f"⏱ {remaining} remaining",
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
    # Cancel the auto-submit job
    jobs = context.job_queue.get_jobs_by_name(f"deadline_{session_data['session_id']}")
    for job in jobs:
        job.schedule_removal()

    result = await api_post("/submit-session", {
        "session_id": session_data["session_id"],
        "bot_session_id": session_data["bot_session_id"],
    })

    context.user_data.pop("session", None)

    await query.edit_message_text(
        "🎉 Assessment Complete!\n\n"
        "Your responses have been submitted.\n"
        "The hiring team will review your results and be in touch.\n\n"
        "Thank you for using TalentCheck!"
    )


async def _auto_submit_job(context: ContextTypes.DEFAULT_TYPE):
    """Auto-submit when server deadline expires."""
    data = context.job.data
    await api_post("/submit-session", {
        "session_id": data["session_id"],
        "bot_session_id": data.get("bot_session_id"),
    })

    await api_post("/proctor-event", {
        "session_id": data["session_id"],
        "type": "timer_expired",
        "detail": "Auto-submitted by bot due to timer expiry",
    })

    await context.bot.send_message(
        chat_id=data["chat_id"],
        text="⏱ Time's up! Your assessment has been auto-submitted.\n\nThank you for using TalentCheck!",
    )


async def cancel_assessment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel button."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("session", None)
    await query.edit_message_text("Assessment cancelled. You can use your invite link again to start.")
