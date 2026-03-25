"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import { sessionApi } from "@/lib/api";

type Option = { key: string; text: string };
type Question = { id: string; text: string; options: Option[]; type: string };
type TestSection = { test_key: string; time_limit_minutes: number; questions: Question[] };

type Answer = { test_key: string; question_id: string; answer: string | null; time_taken_seconds: number };

type State = "loading" | "ready" | "in_progress" | "submitting" | "done" | "error";

function pad(n: number) { return String(n).padStart(2, "0"); }

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${pad(m)}:${pad(s)}`;
}

export default function CandidateTestPage() {
  const { token } = useParams<{ token: string }>();
  const [state, setState] = useState<State>("loading");
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  const [currentTestIdx, setCurrentTestIdx] = useState(0);
  const [currentQIdx, setCurrentQIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [qStartTime, setQStartTime] = useState(Date.now());

  const [totalSeconds, setTotalSeconds] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  const handleTabSwitch = useCallback(() => {
    if (sessionIdRef.current) {
      sessionApi.logEvent(sessionIdRef.current, "tab_switch", "visibility change");
    }
  }, []);

  useEffect(() => {
    document.addEventListener("visibilitychange", handleTabSwitch);
    return () => document.removeEventListener("visibilitychange", handleTabSwitch);
  }, [handleTabSwitch]);

  useEffect(() => {
    sessionApi.start(token)
      .then((res) => {
        setData(res.data);
        sessionIdRef.current = res.data.session_id;
        setTotalSeconds(res.data.seconds_remaining);
        setState("ready");
      })
      .catch((err) => {
        setError(err.response?.data?.detail || "Invalid or expired link.");
        setState("error");
      });
  }, [token]);

  // Timer countdown
  useEffect(() => {
    if (state !== "in_progress") return;
    timerRef.current = setInterval(() => {
      setTotalSeconds((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current!);
          handleSubmit();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [state]);

  const currentTest = data?.tests?.[currentTestIdx] as TestSection | undefined;
  const currentQuestion = currentTest?.questions?.[currentQIdx];
  const totalTests = data?.tests?.length || 0;
  const totalQInSection = currentTest?.questions?.length || 0;

  const selectAnswer = (optionKey: string) => {
    const key = `${currentTest!.test_key}::${currentQuestion!.id}`;
    setAnswers((prev) => ({
      ...prev,
      [key]: {
        test_key: currentTest!.test_key,
        question_id: currentQuestion!.id,
        answer: optionKey,
        time_taken_seconds: Math.round((Date.now() - qStartTime) / 1000),
      },
    }));
  };

  const goNext = () => {
    const key = `${currentTest!.test_key}::${currentQuestion!.id}`;
    if (!answers[key]) {
      setAnswers((prev) => ({
        ...prev,
        [key]: {
          test_key: currentTest!.test_key,
          question_id: currentQuestion!.id,
          answer: null,
          time_taken_seconds: Math.round((Date.now() - qStartTime) / 1000),
        },
      }));
    }
    if (currentQIdx < totalQInSection - 1) {
      setCurrentQIdx((i) => i + 1);
    } else if (currentTestIdx < totalTests - 1) {
      setCurrentTestIdx((i) => i + 1);
      setCurrentQIdx(0);
    } else {
      handleSubmit();
    }
    setQStartTime(Date.now());
  };

  const goPrev = () => {
    if (currentQIdx > 0) {
      setCurrentQIdx((i) => i - 1);
    } else if (currentTestIdx > 0) {
      const prevTest = data.tests[currentTestIdx - 1] as TestSection;
      setCurrentTestIdx((i) => i - 1);
      setCurrentQIdx(prevTest.questions.length - 1);
    }
    setQStartTime(Date.now());
  };

  const handleSubmit = async () => {
    if (state === "submitting" || state === "done") return;
    setState("submitting");
    if (timerRef.current) clearInterval(timerRef.current);
    try {
      await sessionApi.submit(sessionIdRef.current!, Object.values(answers));
      setState("done");
    } catch {
      setState("done");
    }
  };

  const currentAnswer = currentTest && currentQuestion
    ? answers[`${currentTest.test_key}::${currentQuestion.id}`]?.answer
    : null;

  const isLastQuestion = currentTestIdx === totalTests - 1 &&
    currentQIdx === totalQInSection - 1;

  const answeredCount = Object.values(answers).filter((a) => a.answer !== null).length;
  const totalQuestions = data?.tests?.reduce((s: number, t: TestSection) => s + t.questions.length, 0) || 0;

  // ─── Screens ───────────────────────────────────────────────────────────────

  if (state === "loading") {
    return (
      <div className="min-h-screen bg-brand-surface flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-brand-amber border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-brand-muted text-sm">Loading your assessment...</p>
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="min-h-screen bg-brand-surface flex items-center justify-center">
        <div className="text-center max-w-md px-8">
          <div className="w-14 h-14 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-red-500 text-2xl">!</span>
          </div>
          <h1 className="font-display text-2xl font-800 text-brand-dark mb-3">Link Issue</h1>
          <p className="text-brand-muted text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (state === "ready") {
    return (
      <div className="min-h-screen bg-brand-surface flex items-center justify-center p-8">
        <div className="w-full max-w-xl text-center">
          <span className="font-display text-lg font-800 text-brand-dark tracking-tight mb-8 block">
            Talent<span className="text-brand-amber">Check</span>
          </span>
          <h1 className="font-display text-3xl font-800 text-brand-dark mb-3">
            Hello, {data.candidate_name}
          </h1>
          <p className="text-brand-muted text-base mb-2">{data.assessment_title}</p>
          <div className="bg-white border border-brand-border rounded-2xl p-6 mb-8 text-left space-y-3 shadow-card">
            <div className="flex justify-between text-sm">
              <span className="text-brand-muted">Total time</span>
              <span className="text-brand-dark font-mono font-600">{data.total_time_limit_minutes} minutes</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-brand-muted">Sections</span>
              <span className="text-brand-dark font-mono font-600">{data.tests.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-brand-muted">Questions</span>
              <span className="text-brand-dark font-mono font-600">{totalQuestions}</span>
            </div>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-8 text-left">
            <p className="text-amber-800 text-sm font-600 mb-1">Before you begin</p>
            <ul className="text-amber-700/80 text-sm space-y-1 list-disc list-inside">
              <li>Do not switch browser tabs — it will be recorded</li>
              <li>The timer runs continuously and cannot be paused</li>
              <li>Your session will auto-submit when time expires</li>
            </ul>
          </div>
          <button
            onClick={() => setState("in_progress")}
            className="w-full bg-brand-amber text-white font-display font-800 py-4 rounded-xl hover:bg-brand-amber/90 transition-colors text-lg shadow-card"
          >
            Begin Assessment
          </button>
        </div>
      </div>
    );
  }

  if (state === "done") {
    return (
      <div className="min-h-screen bg-brand-surface flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-brand-teal-light rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-brand-teal text-3xl font-700">&check;</span>
          </div>
          <h1 className="font-display text-3xl font-800 text-brand-dark mb-3">Submitted!</h1>
          <p className="text-brand-muted text-base">
            Your assessment has been received. The hiring team will review your results and be in touch.
          </p>
        </div>
      </div>
    );
  }

  if (state === "submitting") {
    return (
      <div className="min-h-screen bg-brand-surface flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-brand-teal border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-brand-muted text-sm">Submitting your answers...</p>
        </div>
      </div>
    );
  }

  // ─── In-progress test UI ────────────────────────────────────────────────────
  const pct = totalSeconds / (data.total_time_limit_minutes * 60);
  const timerUrgent = totalSeconds < 120;

  return (
    <div className="min-h-screen bg-brand-surface flex flex-col">
      {/* Top bar */}
      <header className="bg-white border-b border-brand-border px-6 py-3 flex items-center justify-between sticky top-0 shadow-card z-10">
        <div className="flex items-center gap-3">
          <span className="font-display text-sm font-800 text-brand-dark">
            Talent<span className="text-brand-amber">Check</span>
          </span>
          <span className="text-brand-border">&middot;</span>
          <span className="text-brand-muted text-xs">{data.assessment_title}</span>
        </div>

        {/* Timer */}
        <div className={`flex items-center gap-2 font-mono font-600 text-lg ${timerUrgent ? "text-red-500" : "text-brand-dark"}`}>
          <span>{formatTime(totalSeconds)}</span>
        </div>

        {/* Progress */}
        <div className="text-brand-muted text-xs font-mono">
          {answeredCount}/{totalQuestions} answered
        </div>
      </header>

      {/* Progress bar */}
      <div className="h-1 bg-brand-border">
        <div
          className="h-full bg-brand-amber transition-all duration-1000"
          style={{ width: `${pct * 100}%` }}
        />
      </div>

      {/* Section tabs */}
      <div className="bg-white border-b border-brand-border px-6 py-2 flex gap-3 overflow-x-auto">
        {(data.tests as TestSection[]).map((test, idx) => (
          <button
            key={test.test_key}
            onClick={() => { setCurrentTestIdx(idx); setCurrentQIdx(0); setQStartTime(Date.now()); }}
            className={`text-xs whitespace-nowrap py-1.5 px-3 rounded-full transition-colors font-600 ${
              idx === currentTestIdx
                ? "bg-brand-amber text-white"
                : "text-brand-muted bg-brand-surface hover:bg-brand-border"
            }`}
          >
            {test.test_key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            {" "}
            <span className="opacity-60">
              ({test.questions.filter((q) => answers[`${test.test_key}::${q.id}`]?.answer).length}/{test.questions.length})
            </span>
          </button>
        ))}
      </div>

      {/* Main question area */}
      <main className="flex-1 flex items-start justify-center p-6 pt-10">
        <div className="w-full max-w-2xl">
          {/* Question number */}
          <p className="text-brand-muted text-xs font-mono mb-4">
            Question {currentQIdx + 1} of {totalQInSection}
            {" \u00B7 "}
            {currentTest?.test_key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </p>

          {/* Question text */}
          <h2 className="font-display text-xl font-700 text-brand-dark leading-relaxed mb-8">
            {currentQuestion?.text}
          </h2>

          {/* Options */}
          <div className="space-y-3">
            {currentQuestion?.options.map((opt) => {
              const selected = currentAnswer === opt.key;
              return (
                <button
                  key={opt.key}
                  onClick={() => selectAnswer(opt.key)}
                  className={`w-full text-left px-5 py-4 rounded-xl border transition-all ${
                    selected
                      ? "border-brand-amber bg-brand-amber-light text-brand-dark shadow-card"
                      : "border-brand-border bg-white text-brand-dark/80 hover:border-brand-amber/40 hover:shadow-card"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <span className={`w-7 h-7 rounded-full border flex-shrink-0 flex items-center justify-center text-xs font-700 transition-colors ${
                      selected ? "border-brand-amber bg-brand-amber text-white" : "border-brand-border text-brand-muted"
                    }`}>
                      {opt.key}
                    </span>
                    <span className="text-sm leading-relaxed">{opt.text}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </main>

      {/* Navigation footer */}
      <footer className="bg-white border-t border-brand-border px-6 py-4 flex items-center justify-between shadow-card">
        <button
          onClick={goPrev}
          disabled={currentTestIdx === 0 && currentQIdx === 0}
          className="text-brand-muted text-sm hover:text-brand-dark transition-colors disabled:opacity-20"
        >
          &larr; Previous
        </button>

        <button
          onClick={goNext}
          className={`font-display font-700 text-sm px-6 py-2.5 rounded-lg transition-colors shadow-card ${
            isLastQuestion
              ? "bg-brand-teal text-white hover:opacity-90"
              : "bg-brand-amber text-white hover:bg-brand-amber/90"
          }`}
        >
          {isLastQuestion ? "Submit Assessment" : "Next \u2192"}
        </button>
      </footer>
    </div>
  );
}
