"""Candidate flow: registration, browse tests, test details, results, certificate."""
import base64
import io
import logging
import re
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from ..api_client import api_get, api_post
from ..keyboards import (
    confirm_keyboard,
    candidate_menu_keyboard,
    test_catalog_keyboard,
    test_action_keyboard,
    payment_keyboard,
    result_actions_keyboard,
)
from .. import messages

logger = logging.getLogger(__name__)

# Email regex for basic validation
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?\d{9,15}$")


# ─── Registration conversation handler (message-based) ──────────────────────

async def registration_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages during candidate or employer registration flow."""
    reg_flow = context.user_data.get("reg_flow")
    if not reg_flow:
        return False  # Not in a registration flow

    reg_step = context.user_data.get("reg_step", "")
    text = update.message.text.strip()

    if reg_flow == "candidate":
        return await _candidate_reg_step(update, context, reg_step, text)
    elif reg_flow == "employer":
        from .employer import employer_reg_step
        return await employer_reg_step(update, context, reg_step, text)

    return False


async def _candidate_reg_step(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               step: str, text: str) -> bool:
    """Process a step in candidate registration. Returns True if handled."""
    if step == "name":
        if len(text) < 2:
            await update.message.reply_text("Please enter a valid name (at least 2 characters).")
            return True
        context.user_data["reg_name"] = text
        context.user_data["reg_step"] = "email"
        await update.message.reply_text(messages.CANDIDATE_REG_EMAIL)
        return True

    elif step == "email":
        if not EMAIL_RE.match(text):
            await update.message.reply_text("Please enter a valid email address.")
            return True
        context.user_data["reg_email"] = text.lower()
        context.user_data["reg_step"] = "phone"
        await update.message.reply_text(messages.CANDIDATE_REG_PHONE)
        return True

    elif step == "phone":
        clean_phone = text.replace(" ", "").replace("-", "")
        if not PHONE_RE.match(clean_phone):
            await update.message.reply_text(
                "Please enter a valid phone number (e.g. +251911234567)."
            )
            return True
        context.user_data["reg_phone"] = clean_phone
        context.user_data["reg_step"] = "confirm"

        msg = messages.CANDIDATE_REG_CONFIRM.format(
            full_name=context.user_data["reg_name"],
            email=context.user_data["reg_email"],
            phone=context.user_data["reg_phone"],
        )
        await update.message.reply_text(msg, reply_markup=confirm_keyboard("creg"))
        return True

    return False


async def candidate_reg_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle creg|yes or creg|no confirmation."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split("|", 1)

    if choice == "no":
        # Restart registration
        context.user_data["reg_step"] = "name"
        await query.edit_message_text(messages.CANDIDATE_REG_NAME)
        return

    # choice == "yes" — register via API
    telegram_id = query.from_user.id
    username = query.from_user.username

    result = await api_post("/register-candidate", {
        "full_name": context.user_data["reg_name"],
        "email": context.user_data["reg_email"],
        "phone": context.user_data["reg_phone"],
        "telegram_id": telegram_id,
        "telegram_username": username,
    })

    if result.get("error"):
        await query.edit_message_text(f"Registration failed: {result.get('detail', 'Unknown error')}")
        _clear_reg(context)
        return

    if result.get("already_registered"):
        await query.edit_message_text(
            messages.CANDIDATE_ALREADY_REGISTERED,
            reply_markup=candidate_menu_keyboard(),
        )
        _clear_reg(context)
        return

    name = context.user_data.get("reg_name", "")
    _clear_reg(context)

    await query.edit_message_text(
        messages.CANDIDATE_REG_SUCCESS.format(name=name),
        reply_markup=candidate_menu_keyboard(),
    )


def _clear_reg(context: ContextTypes.DEFAULT_TYPE):
    """Clear registration data from user_data."""
    for key in ("reg_flow", "reg_step", "reg_name", "reg_email", "reg_phone",
                "reg_org_name", "reg_password"):
        context.user_data.pop(key, None)


# ─── Browse tests ────────────────────────────────────────────────────────────

async def browse_tests_action(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Show available tests with prices."""
    try:
        data = await api_get("/tests")
    except Exception:
        await query.edit_message_text("Failed to load tests. Try again later.")
        return

    tests = data.get("tests", [])
    if not tests:
        await query.edit_message_text("No tests available at the moment.")
        return

    await query.edit_message_text(
        messages.TESTS_HEADER,
        reply_markup=test_catalog_keyboard(tests),
    )


async def test_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle test_detail|{test_key} — show test info."""
    query = update.callback_query
    await query.answer()

    _, test_key = query.data.split("|", 1)

    try:
        data = await api_get(f"/tests/{test_key}")
    except Exception:
        await query.edit_message_text("Failed to load test details.")
        return

    msg = messages.TEST_DETAIL.format(
        label=data["label"],
        description=data["description"],
        question_count=data["question_count"],
        time_limit_minutes=data["time_limit_minutes"],
        price_etb=data["price_etb"],
        requirements=data["requirements"],
        sample_question=data["sample_question"],
    )

    await query.edit_message_text(msg, reply_markup=test_action_keyboard(test_key))


# ─── Payment ─────────────────────────────────────────────────────────────────

async def pay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pay|{test_key} — initiate Chapa payment."""
    query = update.callback_query
    await query.answer()

    _, test_key = query.data.split("|", 1)
    telegram_id = query.from_user.id

    # Check if user is registered
    try:
        link_data = await api_get(f"/check-link/{telegram_id}")
    except Exception:
        link_data = {"linked": False}

    if not link_data.get("linked"):
        await query.edit_message_text(
            "You need to register first before purchasing a test.\n"
            "Use /start to register."
        )
        return

    # Get user details from registration
    email = link_data.get("email", "")
    full_name = link_data.get("full_name", "")
    phone = ""

    # If we don't have email from link, use stored reg data
    if not email:
        email = context.user_data.get("reg_email", f"user_{telegram_id}@talentcheck.et")
    if not full_name:
        full_name = context.user_data.get("reg_name", "Candidate")

    result = await api_post("/initiate-payment", {
        "telegram_id": telegram_id,
        "test_key": test_key,
        "email": email,
        "full_name": full_name,
        "phone": phone,
    })

    if result.get("error"):
        await query.edit_message_text(f"Payment error: {result.get('detail')}")
        return

    context.user_data["pending_payment"] = {
        "tx_ref": result["tx_ref"],
        "test_key": test_key,
        "test_label": result["test_label"],
    }

    msg = messages.PAYMENT_INITIATED.format(
        test_label=result["test_label"],
        amount=result["amount"],
    )
    await query.edit_message_text(
        msg,
        reply_markup=payment_keyboard(result["payment_url"], result["tx_ref"]),
    )


async def verify_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verify_pay|{tx_ref} — check Chapa payment status."""
    query = update.callback_query
    await query.answer()

    _, tx_ref = query.data.split("|", 1)

    try:
        result = await api_get(f"/verify-payment/{tx_ref}")
    except Exception:
        await query.edit_message_text(messages.PAYMENT_FAILED)
        return

    if result.get("verified"):
        pending = context.user_data.pop("pending_payment", {})
        test_label = pending.get("test_label", "Test")

        await query.edit_message_text(
            messages.PAYMENT_VERIFIED.format(test_label=test_label),
            reply_markup=candidate_menu_keyboard(),
        )
    else:
        await query.edit_message_text(
            messages.PAYMENT_FAILED,
            reply_markup=payment_keyboard("", tx_ref),
        )


# ─── Results ─────────────────────────────────────────────────────────────────

async def results_action(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Show all results for the current candidate."""
    telegram_id = query.from_user.id

    try:
        data = await api_get(f"/candidate-results/{telegram_id}")
    except Exception:
        await query.edit_message_text("Failed to load results. Try again later.")
        return

    results = data.get("results", [])
    if not results:
        await query.edit_message_text(
            messages.NO_RESULTS,
            reply_markup=candidate_menu_keyboard(),
        )
        return

    text = messages.RESULTS_HEADER
    last_candidate_id = None
    last_passed = False

    for r in results:
        # Build score breakdown
        breakdown = ""
        for test_key, scores in (r.get("scores_by_test") or {}).items():
            test_name = test_key.replace("_", " ").title()
            breakdown += messages.SCORE_LINE.format(
                test_name=test_name,
                percentage=scores.get("percentage", 0),
                label=scores.get("label", "N/A"),
            )

        status = "PASSED" if r.get("passed") else "Did not pass"
        rank_info = ""
        if r.get("rank"):
            rank_info = f"Rank: #{r['rank']}\n"
            if r.get("percentile") is not None:
                rank_info += f"Percentile: {r['percentile']:.0f}th\n"

        text += messages.RESULT_ITEM.format(
            assessment_title=r["assessment_title"],
            org_name=r["org_name"],
            total_score=r["total_score"],
            score_breakdown=breakdown,
            status=status,
            rank_info=rank_info,
        )

        last_candidate_id = r["candidate_id"]
        last_passed = r.get("passed", False)

    if last_candidate_id:
        await query.edit_message_text(
            text,
            reply_markup=result_actions_keyboard(last_candidate_id, last_passed),
        )
    else:
        await query.edit_message_text(text, reply_markup=candidate_menu_keyboard())


# ─── Certificate download ───────────────────────────────────────────────────

async def certificate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cert|{candidate_id} — download PDF certificate."""
    query = update.callback_query
    await query.answer("Generating certificate...")

    _, candidate_id = query.data.split("|", 1)

    try:
        data = await api_get(f"/certificate/{candidate_id}")
    except Exception as e:
        error_msg = str(e)
        if "400" in error_msg:
            await query.edit_message_text(
                messages.CERTIFICATE_NOT_ELIGIBLE.format(score=0),
                reply_markup=candidate_menu_keyboard(),
            )
        else:
            await query.edit_message_text(
                "Failed to generate certificate. Try again later.",
                reply_markup=candidate_menu_keyboard(),
            )
        return

    if isinstance(data, dict) and data.get("error"):
        detail = data.get("detail", "")
        if "below" in str(detail).lower() or "60" in str(detail):
            score = data.get("total_score", 0)
            await query.edit_message_text(
                messages.CERTIFICATE_NOT_ELIGIBLE.format(score=score),
                reply_markup=candidate_menu_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"Error: {detail}",
                reply_markup=candidate_menu_keyboard(),
            )
        return

    # Decode base64 PDF and send as document
    pdf_bytes = base64.b64decode(data["pdf_base64"])
    filename = data.get("filename", "TalentCheck_Certificate.pdf")

    await query.edit_message_text(
        messages.CERTIFICATE_AVAILABLE.format(score=data.get("total_score", 0)),
    )

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=io.BytesIO(pdf_bytes),
        filename=filename,
        caption=f"TalentCheck Certificate - {data.get('candidate_name', '')}",
    )


# ─── Results command ─────────────────────────────────────────────────────────

async def results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /results command."""
    telegram_id = update.effective_user.id

    try:
        data = await api_get(f"/candidate-results/{telegram_id}")
    except Exception:
        await update.message.reply_text("Failed to load results. Try again later.")
        return

    results = data.get("results", [])
    if not results:
        await update.message.reply_text(messages.NO_RESULTS)
        return

    text = messages.RESULTS_HEADER
    last_candidate_id = None
    last_passed = False

    for r in results:
        breakdown = ""
        for test_key, scores in (r.get("scores_by_test") or {}).items():
            test_name = test_key.replace("_", " ").title()
            breakdown += messages.SCORE_LINE.format(
                test_name=test_name,
                percentage=scores.get("percentage", 0),
                label=scores.get("label", "N/A"),
            )

        status = "PASSED" if r.get("passed") else "Did not pass"
        rank_info = ""
        if r.get("rank"):
            rank_info = f"Rank: #{r['rank']}\n"
            if r.get("percentile") is not None:
                rank_info += f"Percentile: {r['percentile']:.0f}th\n"

        text += messages.RESULT_ITEM.format(
            assessment_title=r["assessment_title"],
            org_name=r["org_name"],
            total_score=r["total_score"],
            score_breakdown=breakdown,
            status=status,
            rank_info=rank_info,
        )

        last_candidate_id = r["candidate_id"]
        last_passed = r.get("passed", False)

    if last_candidate_id:
        await update.message.reply_text(
            text,
            reply_markup=result_actions_keyboard(last_candidate_id, last_passed),
        )
    else:
        await update.message.reply_text(text)


# ─── Browse tests command ────────────────────────────────────────────────────

async def browse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /browse command."""
    try:
        data = await api_get("/tests")
    except Exception:
        await update.message.reply_text("Failed to load tests. Try again later.")
        return

    tests = data.get("tests", [])
    if not tests:
        await update.message.reply_text("No tests available at the moment.")
        return

    await update.message.reply_text(
        messages.TESTS_HEADER,
        reply_markup=test_catalog_keyboard(tests),
    )
