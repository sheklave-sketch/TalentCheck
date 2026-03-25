from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import engine, Base
from .routers import auth, organizations, assessments, candidates, sessions, results, telegram, certificates, pricing


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="TalentCheck API",
    version="1.0.0",
    description="Pre-employment assessment platform for Ethiopian organizations",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://talentcheck.vercel.app"],
    allow_origin_regex=r"https://talentcheck.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["organizations"])
app.include_router(assessments.router, prefix="/api/assessments", tags=["assessments"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["candidates"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])
app.include_router(certificates.router, prefix="/api/certificates", tags=["certificates"])
app.include_router(pricing.router, prefix="/api/pricing", tags=["pricing"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "talentcheck-api"}
