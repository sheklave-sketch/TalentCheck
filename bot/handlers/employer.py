"""Employer flow: registration, request demo, invite candidates, view results."""
import logging
import re
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from ..api_client import api_get, api_post
from ..keyboards import (
    confirm_keyboard,
    employer_menu_keyboard,
    assessment_list_keyboard,
    employer_result_actions_keyboard,
    error_recovery_keyboard,
    back_to_menu_keyboard,
)
from .. import messages

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?\d{9,15}$")


# ─── Employer registration (called from registration_message_handler) ────────

async def employer_reg_step(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             step: str, text: str) -> bool:
    """Process a step in employer registration. Returns True if handled."""

    if step == "org_name":
        if len(text) < 2:
            await update.message.reply_text("Please enter a valid organization name.")
            return True
        context.user_data["reg_org_name"] = text
        context.user_data["reg_step"] = "name"
        await update.message.reply_text(messages.EMPLOYER_REG_NAME)
        return True

    elif step == "name":
        if len(text) < 2:
            await update.message.reply_text("Please enter a valid name.")
            return True
        context.user_data["reg_name"] = text
        context.user_data["reg_step"] = "email"
        await update.message.reply_text(messages.EMPLOYER_REG_EMAIL)
        return True

    elif step == "email":
        if not EMAIL_RE.match(text):
            await update.message.reply_text("Please enter a valid email address.")
            return True
        context.user_data["reg_email"] = text.lower()
        context.user_data["reg_step"] = "password"
        await update.message.reply_text(messages.EMPLOYER_REG_PASSWORD)
        return True

    elif step == "password":
        if len(text) < 6:
            await update.message.reply_text("Password must be at least 6 characters.")
            return True
        context.user_data["reg_password"] = text
        context.user_data["reg_step"] = "confirm"

        # Try to delete the password message for security
        try:
            await update.message.delete()
        except Exception:
            pass

        msg = messages.EMPLOYER_REG_CONFIRM.format(
            org_name=context.user_data["reg_org_name"],
            full_name=context.user_data["reg_name"],
            email=context.user_data["reg_email"],
        )
        await update.message.reply_text(msg, reply_markup=confirm_keyboard("ereg"))
        return True

    return False


async def employer_reg_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ereg|yes or ereg|no confirmation."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split("|", 1)

    if choice == "no":
        context.user_data["reg_step"] = "org_name"
        await query.edit_message_text(messages.EMPLOYER_REG_ORG)
        return

    # Register via API
    telegram_id = query.from_user.id
    username = query.from_user.username

    result = await api_post("/register-employer", {
        "org_name": context.user_data.get("reg_org_name", ""),
        "full_name": context.user_data.get("reg_name", ""),
        "email": context.user_data.get("reg_email", ""),
        "password": context.user_data.get("reg_password", ""),
        "telegram_id": telegram_id,
        "telegram_username": username,
    })

    if result.get("error"):
        await query.edit_message_text(f"Registration failed: {result.get('detail', 'Unknown error')}")
        _clear_reg(context)
        return

    name = result.get("full_name", context.user_data.get("reg_name", ""))
    org_name = result.get("org_name", context.user_data.get("reg_org_name", ""))
    _clear_reg(context)

    await query.edit_message_text(
        messages.ONBOARDING_EMPLOYER.format(name=name, org_name=org_name),
        reply_markup=employer_menu_keyboard(),
    )


def _clear_reg(context: ContextTypes.DEFAULT_TYPE):
    for key in ("reg_flow", "reg_step", "reg_name", "reg_email", "reg_phone",
                "reg_org_name", "reg_password"):
        context.user_data.pop(key, None)


# ─── Request Demo ────────────────────────────────────────────────────────────

async def demo_start_action(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Start the demo request flow."""
    context.user_data["demo_flow"] = True
    context.user_data["demo_step"] = "org_name"
    await query.edit_message_text(
        messages.DEMO_REQUEST_INTRO + "\n\n" + messages.DEMO_ORG_NAME
    )


async def demo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /demo command."""
    context.user_data["demo_flow"] = True
    context.user_data["demo_step"] = "org_name"
    await update.message.reply_text(
        messages.DEMO_REQUEST_INTRO + "\n\n" + messages.DEMO_ORG_NAME
    )


async def demo_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle text messages during demo request flow. Returns True if handled."""
    if not context.user_data.get("demo_flow"):
        return False

    step = context.user_data.get("demo_step", "")
    text = update.message.text.strip()

    if step == "org_name":
        context.user_data["demo_org_name"] = text
        context.user_data["demo_step"] = "contact_name"
        await update.message.reply_text(messages.DEMO_CONTACT_NAME)
        return True

    elif step == "contact_name":
        context.user_data["demo_contact_name"] = text
        context.user_data["demo_step"] = "phone"
        await update.message.reply_text(messages.DEMO_PHONE)
        return True

    elif step == "phone":
        clean = text.replace(" ", "").replace("-", "")
        if not PHONE_RE.match(clean):
            await update.message.reply_text("Please enter a valid phone number.")
            return True
        context.user_data["demo_phone"] = clean
        context.user_data["demo_step"] = "email"
        await update.message.reply_text(messages.DEMO_EMAIL)
        return True

    elif step == "email":
        if not EMAIL_RE.match(text):
            await update.message.reply_text("Please enter a valid email address.")
            return True
        context.user_data["demo_email"] = text.lower()
        context.user_data["demo_step"] = "notes"
        await update.message.reply_text(messages.DEMO_NOTES)
        return True

    elif step == "notes":
        notes = "" if text.lower() == "/skip" else text
        context.user_data["demo_notes"] = notes
        context.user_data["demo_step"] = "confirm"

        msg = messages.DEMO_CONFIRM.format(
            org_name=context.user_data["demo_org_name"],
            contact_name=context.user_data["demo_contact_name"],
            phone=context.user_data["demo_phone"],
            email=context.user_data["demo_email"],
            notes=notes or "(none)",
        )
        await update.message.reply_text(msg, reply_markup=confirm_keyboard("demo"))
        return True

    return False


async def demo_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle demo|yes or demo|no confirmation."""
    query = update.callback_query
    await query.answer()

    _, choice = query.data.split("|", 1)

    if choice == "no":
        _clear_demo(context)
        await query.edit_message_text(
            "Demo request cancelled.",
            reply_markup=employer_menu_keyboard(),
        )
        return

    # Submit demo request
    telegram_id = query.from_user.id
    result = await api_post("/request-demo", {
        "org_name": context.user_data.get("demo_org_name", ""),
        "contact_name": context.user_data.get("demo_contact_name", ""),
        "phone": context.user_data.get("demo_phone", ""),
        "email": context.user_data.get("demo_email", ""),
        "notes": context.user_data.get("demo_notes", ""),
        "telegram_id": telegram_id,
    })

    _clear_demo(context)

    if result.get("error"):
        await query.edit_message_text(
            f"Failed to submit: {result.get('detail')}",
            reply_markup=employer_menu_keyboard(),
        )
        return

    await query.edit_message_text(
        messages.DEMO_SUBMITTED,
        reply_markup=employer_menu_keyboard(),
    )


def _clear_demo(context: ContextTypes.DEFAULT_TYPE):
    for key in ("demo_flow", "demo_step", "demo_org_name", "demo_contact_name",
                "demo_phone", "demo_email", "demo_notes"):
        context.user_data.pop(key, None)


# ─── Invite Candidates ──────────────────────────────────────────────────────

async def invite_start_action(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Start the invite candidates flow."""
    context.user_data["invite_flow"] = True
    context.user_data["invite_step"] = "assessment_id"
    await query.edit_message_text(messages.INVITE_ASSESSMENT_ID)


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /invite command."""
    context.user_data["invite_flow"] = True
    context.user_data["invite_step"] = "assessment_id"
    await update.message.reply_text(messages.INVITE_ASSESSMENT_ID)


async def invite_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle text messages during invite flow. Returns True if handled."""
    if not context.user_data.get("invite_flow"):
        return False

    step = context.user_data.get("invite_step", "")
    text = update.message.text.strip()

    if step == "assessment_id":
        context.user_data["invite_assessment_id"] = text
        context.user_data["invite_step"] = "candidates"
        await update.message.reply_text(messages.INVITE_CANDIDATES_PROMPT)
        return True

    elif step == "candidates":
        # Parse candidate list: "Full Name, email" per line
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        candidates = []

        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                candidates.append({
                    "full_name": parts[0],
                    "email": parts[1],
                })
            elif len(parts) == 1:
                candidates.append({
                    "full_name": parts[0],
                    "email": None,
                })

        if not candidates:
            await update.message.reply_text(
                "Could not parse any candidates. Please use the format:\n"
                "Full Name, email@example.com"
            )
            return True

        telegram_id = update.effective_user.id
        result = await api_post("/invite-candidates", {
            "assessment_id": context.user_data["invite_assessment_id"],
            "candidates": candidates,
            "telegram_id": telegram_id,
        })

        _clear_invite(context)

        if result.get("error"):
            await update.message.reply_text(
                messages.INVITE_FAILED.format(detail=result.get("detail", "Unknown error")),
                reply_markup=employer_menu_keyboard(),
            )
            return True

        # Build links list
        invited = result.get("invited", [])
        links_text = ""
        for inv in invited:
            links_text += f"- {inv['full_name']}: {inv['deep_link']}\n"

        await update.message.reply_text(
            messages.INVITE_SUCCESS.format(count=result.get("count", 0), links=links_text),
            reply_markup=employer_menu_keyboard(),
        )
        return True

    return False


def _clear_invite(context: ContextTypes.DEFAULT_TYPE):
    for key in ("invite_flow", "invite_step", "invite_assessment_id"):
        context.user_data.pop(key, None)


# ─── View Results ────────────────────────────────────────────────────────────

async def results_list_action(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    """Show list of assessments for the employer."""
    telegram_id = query.from_user.id

    try:
        data = await api_get(f"/employer-assessments/{telegram_id}")
    except Exception:
        await query.edit_message_text(
            "Failed to load assessments. Try again later.",
            reply_markup=employer_menu_keyboard(),
        )
        return

    if data.get("error"):
        await query.edit_message_text(
            f"Error: {data.get('detail', 'Not linked to employer account.')}",
            reply_markup=employer_menu_keyboard(),
        )
        return

    assessments = data.get("assessments", [])
    if not assessments:
        await query.edit_message_text(
            messages.NO_ASSESSMENTS,
            reply_markup=employer_menu_keyboard(),
        )
        return

    await query.edit_message_text(
        "Select an assessment to view results:",
        reply_markup=assessment_list_keyboard(assessments),
    )


async def employer_results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /employer_results command."""
    telegram_id = update.effective_user.id

    try:
        data = await api_get(f"/employer-assessments/{telegram_id}")
    except Exception:
        await update.message.reply_text(
            "Failed to load assessments. Please try again.",
            reply_markup=back_to_menu_keyboard("employer"),
        )
        return

    if data.get("error"):
        await update.message.reply_text(
            f"Error: {data.get('detail', 'Not linked to employer account.')}",
            reply_markup=back_to_menu_keyboard("employer"),
        )
        return

    assessments = data.get("assessments", [])
    if not assessments:
        await update.message.reply_text(
            messages.NO_ASSESSMENTS,
            reply_markup=employer_menu_keyboard(),
        )
        return

    await update.message.reply_text(
        "Select an assessment to view results:",
        reply_markup=assessment_list_keyboard(assessments),
    )


async def employer_result_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle emp_result|{assessment_id} — show ranked candidate list."""
    query = update.callback_query
    await query.answer()

    _, assessment_id = query.data.split("|", 1)
    telegram_id = query.from_user.id

    try:
        data = await api_get(f"/employer-results/{telegram_id}/{assessment_id}")
    except Exception:
        await query.edit_message_text(
            "Failed to load results.",
            reply_markup=employer_menu_keyboard(),
        )
        return

    if data.get("error"):
        await query.edit_message_text(
            f"Error: {data.get('detail')}",
            reply_markup=employer_menu_keyboard(),
        )
        return

    text = messages.EMPLOYER_RESULTS_HEADER.format(
        title=data.get("assessment_title", "Assessment"),
        total_invited=data.get("total_invited", 0),
        total_completed=data.get("total_completed", 0),
        total_scored=data.get("total_scored", 0),
    )

    candidates = data.get("candidates", [])
    if not candidates:
        text += "No scored results yet."
    else:
        for c in candidates:
            flags = " [FLAGGED]" if c.get("has_flags") else ""
            text += messages.EMPLOYER_RESULT_ROW.format(
                rank=c.get("rank", "-"),
                name=c.get("candidate_name", "Unknown"),
                score=c.get("total_score", 0),
                flags=flags,
            )

    await query.edit_message_text(
        text,
        reply_markup=employer_result_actions_keyboard(assessment_id),
    )
