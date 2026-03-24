"""Reusable inline keyboard builders."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def answer_keyboard(session_id_short: str, question_id: str, options: list[dict]) -> InlineKeyboardMarkup:
    """Build A/B/C/D answer buttons. Callback: ans|{sid}|{qid}|{key}"""
    buttons = []
    for opt in options:
        cb = f"ans|{session_id_short}|{question_id}|{opt['key']}"
        buttons.append([InlineKeyboardButton(f"{opt['key']}) {opt['text']}", callback_data=cb)])
    return InlineKeyboardMarkup(buttons)


def start_assessment_keyboard(invite_token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Start Assessment", callback_data=f"begin|{invite_token}")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_assessment")],
    ])


def continue_section_keyboard(session_id_short: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Continue", callback_data=f"next_section|{session_id_short}")],
    ])


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
    return InlineKeyboardMarkup(buttons)


def practice_again_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Pick Another Category", callback_data="practice_again")],
        [InlineKeyboardButton("Done", callback_data="practice_done")],
    ])
