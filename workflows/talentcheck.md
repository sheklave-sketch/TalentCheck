# TalentCheck — Master Workflow

## Objective
Operate and extend the TalentCheck pre-employment assessment SaaS platform for Ethiopian organizations.

## Architecture

```
talentcheck/
├── api/                    ← FastAPI backend (Python)
│   ├── main.py             ← App entry point, router registration
│   ├── database.py         ← Async SQLAlchemy engine + session
│   ├── config.py           ← Settings from .env
│   ├── models/models.py    ← All ORM models
│   ├── routers/            ← auth, assessments, candidates, sessions, results, organizations
│   └── services/           ← scoring_engine, invitation, pdf_generator
├── web/                    ← Next.js 14 frontend (TypeScript)
│   ├── app/                ← App Router pages
│   │   ├── (auth)/         ← login, register
│   │   ├── dashboard/      ← employer assessment list
│   │   ├── assessments/    ← new, [id]/results, [id]/invite
│   │   └── test/[token]/   ← candidate test-taking interface
│   └── lib/api.ts          ← All API calls (axios)
├── content/                ← Question bank JSON files (6 tests)
├── .env.example            ← All required env vars
└── start_dev.bat           ← Launch both servers
```

## Running Locally

```bash
# 1. Copy and fill env
cp .env.example .env

# 2. Install backend deps
cd api && pip install -r requirements.txt

# 3. Install frontend deps
cd web && npm install

# 4. Start both servers
start_dev.bat
# API: http://localhost:8000  |  Docs: http://localhost:8000/docs
# Web: http://localhost:3000
```

## Key Design Rules

1. **Answer keys never reach the client** — `scoring_engine.py` strips `correct_answer` before questions are sent. Scoring is 100% server-side.
2. **Timer is server-authoritative** — `server_deadline` is set at session start. Submissions after deadline are accepted but flagged. JS timer is for display only.
3. **Anti-cheat is non-blocking** — Tab switches and visibility changes are logged as `proctoring_flags`, not used to fail the candidate. HR reviews flags and decides.
4. **Invite tokens are UUIDs** — One-time use, per-candidate, not tied to any account.
5. **Scoring is triggered manually** by HR (POST `/api/results/score/{assessment_id}`) after candidates complete.

## Data Flow

```
Employer creates assessment (test_config: [{test_key, weight, time_limit}])
    → activates it
    → invites candidates (email + optional SMS)

Candidate receives link → /test/{token}
    → GET /api/sessions/start/{token}   (returns questions, no answers)
    → answers questions in browser
    → POST /api/sessions/submit         (sends responses server-side)

HR clicks "Run Scoring"
    → POST /api/results/score/{assessment_id}
    → scores each submitted session, computes percentile + rank
    → GET /api/results/assessment/{assessment_id}  → ranked list
    → GET /api/results/pdf/{candidate_id}          → PDF report
    → GET /api/results/export/{assessment_id}      → Excel export
```

## Question Bank Format

Each file in `content/` follows this schema:
```json
{
  "key": "test_key",
  "label": "Display Name",
  "questions": [
    {
      "id": "unique_id",
      "type": "mcq",
      "category": "subcategory",
      "text": "Question text",
      "options": [{"key": "A", "text": "..."}, ...],
      "correct_answer": "A"
    }
  ]
}
```

## Adding a New Test

1. Create `content/{new_key}.json` following the schema above
2. Add entry to `AVAILABLE_TESTS` list in `api/routers/assessments.py`
3. No other changes needed — scoring engine loads tests dynamically

## Scoring Logic

- Each test scores independently: `raw_correct / total_questions * 100`
- Labels: ≥80% Excellent, ≥60% Good, ≥40% Fair, <40% Below Average
- Overall score = weighted average across selected tests (weights set per assessment)
- Percentile = % of candidates in same assessment scoring below this candidate
- Rank = 1 = highest scorer

## SaaS Plans

| Plan       | Candidates/month | Assessments |
|------------|-----------------|-------------|
| Starter    | 10              | 1 active    |
| Growth     | 500             | 10 active   |
| Enterprise | Unlimited       | Unlimited   |

Enforcement TODO: Add middleware check in `candidates.py` invite route against `org.candidates_used_this_month`.

## Phase 2 Additions (not yet built)

- Amharic / Afaan Oromo question translations
- Custom test builder (employer-defined questions)
- Video response questions
- Webcam snapshot via MediaDevices API → Supabase Storage
- Chapa payment integration for subscription billing
- API for ATS integration

## Known Constraints

- `content/` JSON files are loaded from disk on each scoring call — cache in memory for production
- PDF generation uses ReportLab (synchronous) — run in a background thread for large batches
- SMS via Africa's Talking — sandbox mode by default, set `AFRICAS_TALKING_USERNAME=sandbox` for testing
