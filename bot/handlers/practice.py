"""Free practice test flow — no auth, no timer."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..api_client import api_get
from ..keyboards import practice_category_keyboard, practice_again_keyboard


async def practice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /practice command."""
    await update.message.reply_text(
        "🧠 Practice Tests\n\n"
        "Pick a category to try 5 sample questions.\n"
        "No timer, no login — just practice!",
        reply_markup=practice_category_keyboard(),
    )


async def practice_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection: practice|{test_key}."""
    query = update.callback_query
    await query.answer()

    _, test_key = query.data.split("|", 1)

    try:
        data = await api_get(f"/practice-questions/{test_key}", {"count": 5})
    except Exception:
        await query.edit_message_text("Failed to load practice questions. Try again later.")
        return

    questions = data["questions"]
    label = data["label"]

    context.user_data["practice"] = {
        "questions": questions,
        "label": label,
        "current": 0,
        "correct": 0,
    }

    await query.edit_message_text(
        f"📖 Practice: {label}\n"
        f"5 sample questions — answers shown after each.\n\n"
        f"Let's go!"
    )

    await _send_practice_question(query.message.chat_id, context)


async def _send_practice_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Send the current practice question."""
    p = context.user_data["practice"]
    q = p["questions"][p["current"]]
    total = len(p["questions"])

    text = f"Question {p['current'] + 1}/{total}\n\n{q['text']}"

    buttons = []
    for opt in q["options"]:
        cb = f"pans|{p['current']}|{opt['key']}"
        buttons.append([InlineKeyboardButton(f"{opt['key']}) {opt['text']}", callback_data=cb)])

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(buttons))


async def practice_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle practice answer: pans|{index}|{key}."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")
    if len(parts) != 3:
        return

    _, q_index, answer_key = parts
    q_index = int(q_index)

    p = context.user_data.get("practice")
    if not p or q_index != p["current"]:
        return

    q = p["questions"][q_index]
    correct = q["correct_answer"]
    is_correct = answer_key == correct

    if is_correct:
        p["correct"] += 1
        feedback = f"✅ Correct! The answer is {correct}."
    else:
        feedback = f"❌ Incorrect. The correct answer is {correct}."

    await query.edit_message_text(f"{q['text']}\n\nYour answer: {answer_key}\n{feedback}")

    p["current"] += 1

    if p["current"] < len(p["questions"]):
        await _send_practice_question(query.message.chat_id, context)
    else:
        score = p["correct"]
        total = len(p["questions"])
        pct = int((score / total) * 100)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                f"📊 Practice Complete!\n\n"
                f"You got {score}/{total} correct ({pct}%).\n\n"
                f"Want to try another category?"
            ),
            reply_markup=practice_again_keyboard(),
        )


async def practice_again_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Pick Another Category' button."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("practice", None)
    await query.edit_message_text(
        "🧠 Practice Tests\n\nPick a category:",
        reply_markup=practice_category_keyboard(),
    )


async def practice_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Done' button."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("practice", None)
    await query.edit_message_text("Thanks for practicing! Use /practice anytime to try again.")
