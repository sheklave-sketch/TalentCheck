"""Reusable inline keyboard builders."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ─── Role selection ──────────────────────────────────────────────────────────

def role_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("I'm a Candidate", callback_data="role|candidate")],
        [InlineKeyboardButton("I'm an Employer", callback_data="role|employer")],
    ])


# ─── Candidate menu ─────────────────────────────────────────────────────────

def candidate_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Browse Tests", callback_data="menu|browse_tests")],
        [InlineKeyboardButton("Practice Tests (Free)", callback_data="menu|practice")],
        [InlineKeyboardButton("My Results", callback_data="menu|results")],
        [InlineKeyboardButton("Help", callback_data="menu|help")],
    ])


# ─── Employer menu ──────────────────────────────────────────────────────────

def employer_menu_keyboard(telegram_id: int | None = None) -> InlineKeyboardMarkup:
    dashboard_url = "https://talentcheck-tau.vercel.app"
    if telegram_id:
        dashboard_url = f"https://talentcheck-tau.vercel.app/?tg_id={telegram_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Request Demo", callback_data="emenu|demo")],
        [InlineKeyboardButton("Invite Candidates", callback_data="emenu|invite")],
        [InlineKeyboardButton("View Results", callback_data="emenu|results")],
        [InlineKeyboardButton("Open Web Dashboard", url=dashboard_url)],
        [InlineKeyboardButton("Help", callback_data="emenu|help")],
    ])


# ─── Back to menu ───────────────────────────────────────────────────────────

def back_to_menu_keyboard(role: str = "candidate") -> InlineKeyboardMarkup:
    """Single 'Back to Menu' button."""
    cb = "emenu|back" if role == "employer" else "menu|back"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Back to Menu", callback_data=cb)],
    ])


def fallback_keyboard() -> InlineKeyboardMarkup:
    """Shown when bot doesn't understand the input."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Main Menu", callback_data="menu|back")],
        [InlineKeyboardButton("Help", callback_data="menu|help")],
    ])


def error_recovery_keyboard(retry_callback: str, role: str = "candidate") -> InlineKeyboardMarkup:
    """Retry + Back to Menu for error states."""
    back_cb = "emenu|back" if role == "employer" else "menu|back"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Try Again", callback_data=retry_callback)],
        [InlineKeyboardButton("Back to Menu", callback_data=back_cb)],
    ])


# ─── Confirmation ────────────────────────────────────────────────────────────

def confirm_keyboard(prefix: str = "confirm") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Yes, confirm", callback_data=f"{prefix}|yes"),
            InlineKeyboardButton("No, redo", callback_data=f"{prefix}|no"),
        ],
    ])


# ─── Test catalog ────────────────────────────────────────────────────────────

def test_catalog_keyboard(tests: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for t in tests:
        label = f"{t['label']} — {t['price_etb']} ETB"
        buttons.append([InlineKeyboardButton(label, callback_data=f"test_detail|{t['key']}")])
    buttons.append([InlineKeyboardButton("Back to Menu", callback_data="menu|back")])
    return InlineKeyboardMarkup(buttons)


def test_action_keyboard(test_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Pay & Take Test", callback_data=f"pay|{test_key}")],
        [InlineKeyboardButton("Practice (Free)", callback_data=f"practice|{test_key}")],
        [InlineKeyboardButton("Back to Tests", callback_data="menu|browse_tests")],
    ])


# ─── Payment ─────────────────────────────────────────────────────────────────

def payment_keyboard(payment_url: str, tx_ref: str) -> InlineKeyboardMarkup:
    buttons = []
    if payment_url:
        buttons.append([InlineKeyboardButton("Pay with Chapa", url=payment_url)])
    buttons.append([InlineKeyboardButton("Verify Payment", callback_data=f"verify_pay|{tx_ref}")])
    buttons.append([InlineKeyboardButton("Cancel", callback_data="menu|browse_tests")])
    return InlineKeyboardMarkup(buttons)


# ─── Assessment ──────────────────────────────────────────────────────────────

def answer_keyboard(session_id_short: str, question_id: str, options: list[dict]) -> InlineKeyboardMarkup:
    """Build short A/B/C/D answer buttons in a single row. Options text shown in message body."""
    buttons = [
        InlineKeyboardButton(opt["key"], callback_data=f"ans|{session_id_short}|{question_id}|{opt['key']}")
        for opt in options
    ]
    return InlineKeyboardMarkup([buttons])


def start_assessment_keyboard(invite_token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Start Assessment", callback_data=f"begin|{invite_token}")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_assessment")],
    ])


def continue_section_keyboard(session_id_short: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Continue", callback_data=f"next_section|{session_id_short}")],
    ])


# ─── Results ─────────────────────────────────────────────────────────────────

def result_actions_keyboard(candidate_id: str, passed: bool) -> InlineKeyboardMarkup:
    buttons = []
    if passed:
        buttons.append([InlineKeyboardButton("Download Certificate", callback_data=f"cert|{candidate_id}")])
    buttons.append([InlineKeyboardButton("Back to Menu", callback_data="menu|back")])
    return InlineKeyboardMarkup(buttons)


# ─── Practice ────────────────────────────────────────────────────────────────

def practice_category_keyboard() -> InlineKeyboardMarkup:
    categories = [
        ("Cognitive Ability", "cognitive"),
        ("English Proficiency", "english"),
        ("Customer Service", "customer_service"),
        ("Computer Skills", "computer_skills"),
        ("Integrity & Ethics", "integrity"),
        ("Developer (Junior)", "developer_basic"),
    ]
    buttons = [[InlineKeyboardButton(label, callback_data=f"practice|{key}")] for label, key in categories]
    buttons.append([InlineKeyboardButton("Back to Menu", callback_data="menu|back")])
    return InlineKeyboardMarkup(buttons)


def practice_again_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Pick Another Category", callback_data="practice_again")],
        [InlineKeyboardButton("Back to Menu", callback_data="menu|back")],
    ])


# ─── Employer results ────────────────────────────────────────────────────────

def assessment_list_keyboard(assessments: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for a in assessments:
        label = f"{a['title']} ({a['candidate_count']} candidates)"
        buttons.append([InlineKeyboardButton(label, callback_data=f"emp_result|{a['id']}")])
    buttons.append([InlineKeyboardButton("Back to Menu", callback_data="emenu|back")])
    return InlineKeyboardMarkup(buttons)


def employer_result_actions_keyboard(assessment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("View on Dashboard",
                              url=f"https://talentcheck-tau.vercel.app/dashboard/assessments/{assessment_id}")],
        [InlineKeyboardButton("Back to Assessments", callback_data="emenu|results")],
    ])
