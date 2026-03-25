"""All bot message templates. Centralized for easy editing."""


# ─── Welcome / Start ────────────────────────────────────────────────────────

WELCOME = (
    "Welcome to TalentCheck Ethiopia!\n\n"
    "Hire by Skill, Not CV.\n\n"
    "What brings you here today?"
)

WELCOME_BACK_CANDIDATE = (
    "Welcome back, {name}!\n\n"
    "What would you like to do?"
)

WELCOME_BACK_EMPLOYER = (
    "Welcome back, {name}!\n\n"
    "Organization: {org_name}\n\n"
    "What would you like to do?"
)


# ─── Candidate Registration ─────────────────────────────────────────────────

CANDIDATE_REG_NAME = "Let's get you registered!\n\nWhat is your full name?"
CANDIDATE_REG_EMAIL = "Great! Now enter your email address:"
CANDIDATE_REG_PHONE = "And your phone number (e.g. +251911234567):"
CANDIDATE_REG_CONFIRM = (
    "Please confirm your details:\n\n"
    "Name: {full_name}\n"
    "Email: {email}\n"
    "Phone: {phone}\n\n"
    "Is this correct?"
)
CANDIDATE_REG_SUCCESS = (
    "Registration complete! Welcome to TalentCheck, {name}.\n\n"
    "You can now:\n"
    "- Browse available tests\n"
    "- Take practice tests for free\n"
    "- Complete employer-assigned assessments\n\n"
    "Use the menu below to get started."
)
CANDIDATE_ALREADY_REGISTERED = (
    "You're already registered! Use the menu to browse tests or check results."
)


# ─── Employer Registration ───────────────────────────────────────────────────

EMPLOYER_REG_ORG = "Let's set up your employer account.\n\nWhat is your organization name?"
EMPLOYER_REG_NAME = "What is your full name?"
EMPLOYER_REG_EMAIL = "Enter your work email address:"
EMPLOYER_REG_PASSWORD = (
    "Create a password for your account:\n\n"
    "(This will also work for the web dashboard at talentcheck-tau.vercel.app)"
)
EMPLOYER_REG_CONFIRM = (
    "Please confirm your details:\n\n"
    "Organization: {org_name}\n"
    "Name: {full_name}\n"
    "Email: {email}\n\n"
    "Is this correct?"
)
EMPLOYER_REG_SUCCESS = (
    "Account created! Welcome to TalentCheck, {name}.\n\n"
    "Organization: {org_name}\n\n"
    "You can now:\n"
    "- Request a demo\n"
    "- Invite candidates to assessments\n"
    "- View assessment results\n"
    "- Access the full web dashboard\n\n"
    "Use the menu below to get started."
)


# ─── Browse Tests ────────────────────────────────────────────────────────────

TESTS_HEADER = (
    "Available Tests\n\n"
    "Select a test to see details, sample questions, and pricing:"
)

TEST_DETAIL = (
    "{label}\n\n"
    "{description}\n\n"
    "Questions: {question_count}\n"
    "Time Limit: {time_limit_minutes} minutes\n"
    "Price: {price_etb} ETB\n\n"
    "Requirements:\n{requirements}\n\n"
    "Sample Question:\n{sample_question}"
)


# ─── Payment ─────────────────────────────────────────────────────────────────

PAYMENT_INITIATED = (
    "Payment Summary\n\n"
    "Test: {test_label}\n"
    "Amount: {amount} ETB\n\n"
    "Click the button below to pay via Chapa.\n"
    "After payment, tap 'Verify Payment' to confirm."
)

PAYMENT_VERIFIED = (
    "Payment confirmed!\n\n"
    "Test: {test_label}\n"
    "You can now start the test. Good luck!"
)

PAYMENT_FAILED = (
    "Payment could not be verified.\n\n"
    "If you've already paid, please wait a moment and try verifying again.\n"
    "Contact support if the issue persists."
)


# ─── Assessment Flow ─────────────────────────────────────────────────────────

ASSESSMENT_WELCOME = (
    "Welcome to TalentCheck, {candidate_name}!\n\n"
    "{org_name} has invited you to complete:\n"
    "{assessment_title}\n\n"
    "Tests included:\n{tests_list}\n\n"
    "Total time: {total_time_limit_minutes} minutes\n"
    "Total questions: {total_questions}\n\n"
    "Once you start, the timer begins and cannot be paused."
)

QUESTION_TEMPLATE = (
    "{test_label} -- Question {q_num}/{q_total}\n"
    "Time remaining: {time_remaining}\n\n"
    "{question_text}"
)

SECTION_COMPLETE = (
    "{test_label} -- Complete!\n\n"
    "Next: {next_label}\n"
    "Time remaining: {time_remaining}"
)

ASSESSMENT_COMPLETE = (
    "Assessment Complete!\n\n"
    "Your responses have been submitted.\n"
    "The hiring team will review your results and be in touch.\n\n"
    "Thank you for using TalentCheck!"
)

TIME_EXPIRED = (
    "Time's up! Your assessment has been auto-submitted.\n\n"
    "Thank you for using TalentCheck!"
)


# ─── Results ─────────────────────────────────────────────────────────────────

RESULTS_HEADER = "Your Test Results\n\n"

RESULT_ITEM = (
    "Assessment: {assessment_title}\n"
    "Organization: {org_name}\n"
    "Overall Score: {total_score:.1f}%\n"
    "{score_breakdown}"
    "Status: {status}\n"
    "{rank_info}"
    "---\n"
)

SCORE_LINE = "  {test_name}: {percentage:.1f}% ({label})\n"

NO_RESULTS = "You don't have any test results yet.\n\nComplete an assessment to see your scores here."

CERTIFICATE_AVAILABLE = (
    "Congratulations! You passed with {score:.1f}%.\n"
    "Your certificate is ready!"
)

CERTIFICATE_NOT_ELIGIBLE = (
    "Your score of {score:.1f}% is below the passing threshold of 60%.\n"
    "Certificates are only available for scores of 60% and above.\n\n"
    "Consider retaking the test to improve your score."
)


# ─── Employer ────────────────────────────────────────────────────────────────

DEMO_REQUEST_INTRO = (
    "Request a Demo\n\n"
    "We'll collect your contact information and have our team reach out within 24 hours."
)
DEMO_ORG_NAME = "What is your organization name?"
DEMO_CONTACT_NAME = "Your full name:"
DEMO_PHONE = "Your phone number:"
DEMO_EMAIL = "Your email address:"
DEMO_NOTES = "Any specific questions or requirements? (or send /skip to skip)"
DEMO_CONFIRM = (
    "Demo Request Summary\n\n"
    "Organization: {org_name}\n"
    "Contact: {contact_name}\n"
    "Phone: {phone}\n"
    "Email: {email}\n"
    "Notes: {notes}\n\n"
    "Submit this request?"
)
DEMO_SUBMITTED = (
    "Demo request submitted!\n\n"
    "Our team will contact you within 24 hours.\n"
    "Thank you for your interest in TalentCheck!"
)

INVITE_ASSESSMENT_ID = (
    "Invite Candidates\n\n"
    "Enter the Assessment ID you want to invite candidates to.\n"
    "(You can find this on the web dashboard.)"
)
INVITE_CANDIDATES_PROMPT = (
    "Now enter candidate details, one per line:\n"
    "Format: Full Name, email@example.com\n\n"
    "Example:\n"
    "Abebe Kebede, abebe@email.com\n"
    "Tigist Haile, tigist@email.com\n\n"
    "Send all candidates in one message."
)
INVITE_SUCCESS = (
    "Invitations sent!\n\n"
    "{count} candidate(s) invited.\n\n"
    "Deep links:\n{links}"
)
INVITE_FAILED = "Failed to invite candidates: {detail}"

EMPLOYER_RESULTS_HEADER = (
    "Assessment Results: {title}\n\n"
    "Invited: {total_invited} | Completed: {total_completed} | Scored: {total_scored}\n\n"
)
EMPLOYER_RESULT_ROW = (
    "#{rank} {name} — {score:.1f}%{flags}\n"
)

NO_ASSESSMENTS = "You don't have any assessments yet.\n\nCreate one on the web dashboard to get started."


# ─── Practice ────────────────────────────────────────────────────────────────

PRACTICE_WELCOME = (
    "Practice Tests\n\n"
    "Pick a category to try 5 sample questions.\n"
    "No timer, no login — just practice!"
)

PRACTICE_START = (
    "Practice: {label}\n"
    "5 sample questions — answers shown after each.\n\n"
    "Let's go!"
)

PRACTICE_CORRECT = "Correct! The answer is {correct}."
PRACTICE_INCORRECT = "Incorrect. The correct answer is {correct}."

PRACTICE_COMPLETE = (
    "Practice Complete!\n\n"
    "You got {score}/{total} correct ({pct}%).\n\n"
    "Want to try another category?"
)


# ─── Help ────────────────────────────────────────────────────────────────────

HELP_TEXT = (
    "TalentCheck Bot — Help\n\n"
    "Commands:\n"
    "/start — Welcome message & registration\n"
    "/practice — Free practice tests (5 questions, with answers)\n"
    "/browse — Browse available tests\n"
    "/results — View your test results\n"
    "/link — Link your Telegram to your web account\n"
    "/help — This help message\n"
    "/cancel — Cancel current operation\n\n"
    "For Employers:\n"
    "/demo — Request a product demo\n"
    "/invite — Invite candidates to an assessment\n"
    "/employer_results — View assessment results\n\n"
    "If you received an assessment invite link, tap it to start your test.\n\n"
    "Questions? Visit talentcheck-tau.vercel.app"
)

CANCEL_MESSAGE = "Operation cancelled. Use /start to begin again."
