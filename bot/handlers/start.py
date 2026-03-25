"""Handle /start, /menu, role selection, and deep links."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..api_client import api_get
from ..keyboards import (
    role_selection_keyboard,
    candidate_menu_keyboard,
    employer_menu_keyboard,
    start_assessment_keyboard,
    back_to_menu_keyboard,
)
from .. import messages

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start and /start {invite_token}."""
    args = context.args

    # Deep link: /start {invite_token}
    if args and len(args) == 1:
        invite_token = args[0]
        await _handle_invite_link(update, context, invite_token)
        return

    # Check if user is already registered
    telegram_id = update.effective_user.id
    try:
        link_data = await api_get(f"/check-link/{telegram_id}")
    except Exception:
        link_data = {"linked": False}

    if link_data.get("linked"):
        role = link_data.get("role")
        if role == "employer":
            msg = messages.WELCOME_BACK_EMPLOYER.format(
                name=link_data.get("full_name", ""),
                org_name=link_data.get("org_name", "your organization"),
            )
            await update.message.reply_text(msg, reply_markup=employer_menu_keyboard(telegram_id))
            return
        elif role in ("candidate", "candidate_registered"):
            msg = messages.WELCOME_BACK_CANDIDATE.format(
                name=link_data.get("full_name", "there"),
            )
            await update.message.reply_text(msg, reply_markup=candidate_menu_keyboard(telegram_id))
            return

    # New user — show role selection
    await update.message.reply_text(messages.WELCOME, reply_markup=role_selection_keyboard())


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu — show the main menu for the user's role."""
    telegram_id = update.effective_user.id
    try:
        link_data = await api_get(f"/check-link/{telegram_id}")
    except Exception:
        link_data = {"linked": False}

    if link_data.get("linked"):
        role = link_data.get("role")
        if role == "employer":
            await update.message.reply_text(
                messages.WELCOME_BACK_EMPLOYER.format(
                    name=link_data.get("full_name", ""),
                    org_name=link_data.get("org_name", ""),
                ),
                reply_markup=employer_menu_keyboard(telegram_id),
            )
        else:
            await update.message.reply_text(
                messages.WELCOME_BACK_CANDIDATE.format(
                    name=link_data.get("full_name", "there"),
                ),
                reply_markup=candidate_menu_keyboard(telegram_id),
            )
    else:
        await update.message.reply_text(
            messages.NOT_REGISTERED,
            reply_markup=role_selection_keyboard(),
        )


async def role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle role|candidate or role|employer callback."""
    query = update.callback_query
    await query.answer()

    _, role = query.data.split("|", 1)

    if role == "candidate":
        # Start candidate registration conversation
        context.user_data["reg_flow"] = "candidate"
        context.user_data["reg_step"] = "name"
        await query.edit_message_text(messages.CANDIDATE_REG_NAME)

    elif role == "employer":
        # Start employer registration conversation
        context.user_data["reg_flow"] = "employer"
        context.user_data["reg_step"] = "org_name"
        await query.edit_message_text(messages.EMPLOYER_REG_ORG)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle candidate menu selections: menu|browse_tests, menu|practice, etc."""
    query = update.callback_query
    await query.answer()

    _, action = query.data.split("|", 1)

    if action == "browse_tests":
        from .candidate import browse_tests_action
        await browse_tests_action(query, context)

    elif action == "practice":
        from .practice import practice_action
        await practice_action(query, context)

    elif action == "results":
        from .candidate import results_action
        await results_action(query, context)

    elif action == "help":
        await query.edit_message_text(
            messages.HELP_TEXT,
            reply_markup=back_to_menu_keyboard("candidate"),
        )

    elif action == "back":
        # Return to main candidate menu
        telegram_id = query.from_user.id
        try:
            link_data = await api_get(f"/check-link/{telegram_id}")
            role = link_data.get("role", "")
        except Exception:
            role = ""

        if role == "employer":
            await query.edit_message_text(
                messages.WELCOME_BACK_EMPLOYER.format(
                    name=link_data.get("full_name", ""),
                    org_name=link_data.get("org_name", ""),
                ),
                reply_markup=employer_menu_keyboard(telegram_id),
            )
        else:
            name = "there"
            try:
                name = link_data.get("full_name", "there") if role else "there"
            except Exception:
                pass
            await query.edit_message_text(
                messages.WELCOME_BACK_CANDIDATE.format(name=name),
                reply_markup=candidate_menu_keyboard(telegram_id),
            )


async def employer_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle employer menu selections: emenu|demo, emenu|invite, etc."""
    query = update.callback_query
    await query.answer()

    _, action = query.data.split("|", 1)

    if action == "demo":
        from .employer import demo_start_action
        await demo_start_action(query, context)

    elif action == "invite":
        from .employer import invite_start_action
        await invite_start_action(query, context)

    elif action == "results":
        from .employer import results_list_action
        await results_list_action(query, context)

    elif action == "help":
        await query.edit_message_text(
            messages.HELP_TEXT,
            reply_markup=back_to_menu_keyboard("employer"),
        )

    elif action == "back":
        telegram_id = query.from_user.id
        try:
            link_data = await api_get(f"/check-link/{telegram_id}")
        except Exception:
            link_data = {}
        await query.edit_message_text(
            messages.WELCOME_BACK_EMPLOYER.format(
                name=link_data.get("full_name", ""),
                org_name=link_data.get("org_name", ""),
            ),
            reply_markup=employer_menu_keyboard(telegram_id),
        )


async def _handle_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE, invite_token: str):
    """Handle a deep link with an invite token for an assessment."""
    try:
        data = await api_get(f"/candidate-by-token/{invite_token}")
    except Exception:
        await update.message.reply_text(
            "Invalid or expired invite link.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    if isinstance(data, dict) and data.get("error"):
        await update.message.reply_text(
            f"Error: {data.get('detail', 'Unknown error')}",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    tests_list = "\n".join(
        f"  - {t['test_key'].replace('_', ' ').title()} ({t['time_limit_minutes']} min)"
        for t in data["test_config"]
    )

    msg = messages.ASSESSMENT_WELCOME.format(
        candidate_name=data["candidate_name"],
        org_name=data["org_name"],
        assessment_title=data["assessment_title"],
        tests_list=tests_list,
        total_time_limit_minutes=data["total_time_limit_minutes"],
        total_questions=data["total_questions"],
    )
    await update.message.reply_text(msg, reply_markup=start_assessment_keyboard(invite_token))
