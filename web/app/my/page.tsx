"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

type ResultItem = {
  candidate_id: string;
  candidate_name: string;
  assessment_title: string;
  org_name: string;
  total_score: number;
  scores_by_test: Record<string, { percentage: number; label: string; raw_score: number; total_questions: number }>;
  percentile: number | null;
  rank: number | null;
  passed: boolean;
  scored_at: string | null;
};

type CertItem = {
  id: string;
  certificate_number: string;
  candidate_name: string;
  test_label: string;
  score_percentage: number;
  performance_label: string;
  issued_at: string | null;
  verify_url: string;
};

type TestItem = {
  key: string;
  label: string;
  description: string;
  question_count: number;
  time_limit_minutes: number;
  price_etb: number;
};

type Tab = "results" | "certificates" | "tests";

function ScoreBadge({ label }: { label: string }) {
  const colors: Record<string, string> = {
    "Excellent": "bg-emerald-50 text-emerald-700 border-emerald-200",
    "Good": "bg-amber-50 text-amber-700 border-amber-200",
    "Fair": "bg-gray-100 text-gray-600 border-gray-200",
    "Below Average": "bg-red-50 text-red-600 border-red-200",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-600 border ${colors[label] || "bg-gray-50 text-gray-400 border-gray-200"}`}>
      {label}
    </span>
  );
}

export default function CandidateDashboard() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("results");
  const [results, setResults] = useState<ResultItem[]>([]);
  const [certs, setCerts] = useState<CertItem[]>([]);
  const [tests, setTests] = useState<TestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [tgId, setTgId] = useState<string | null>(null);

  useEffect(() => {
    const id = localStorage.getItem("tc_tg_id");
    if (!id) {
      router.replace("/login");
      return;
    }
    setTgId(id);

    Promise.all([
      api.get(`/api/my/results/${id}`).then((r) => setResults(r.data.results || [])).catch(() => {}),
      api.get(`/api/my/certificates/${id}`).then((r) => setCerts(r.data.certificates || [])).catch(() => {}),
      api.get("/api/my/tests").then((r) => setTests(r.data.tests || [])).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [router]);

  const copyLink = (url: string) => {
    navigator.clipboard.writeText(url);
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "\u2014";
    return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  };

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "results", label: "My Results", count: results.length },
    { key: "certificates", label: "Certificates", count: certs.length },
    { key: "tests", label: "Browse Tests", count: tests.length },
  ];

  return (
    <div className="min-h-screen bg-brand-surface">
      {/* Nav */}
      <nav className="bg-white border-b border-brand-border px-6 py-4 flex items-center justify-between shadow-card">
        <span className="font-display text-lg font-800 text-brand-dark tracking-tight">
          Talent<span className="text-brand-amber">Check</span>
        </span>
        <button
          onClick={() => { localStorage.removeItem("tc_tg_id"); router.push("/login"); }}
          className="text-brand-muted text-sm hover:text-brand-dark transition-colors"
        >
          Sign out
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display text-2xl font-800 text-brand-dark mb-1">My Dashboard</h1>
          <p className="text-brand-muted text-sm">View your results, certificates, and available tests</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-8 bg-white border border-brand-border rounded-xl p-1 shadow-card">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-600 transition-colors ${
                tab === t.key
                  ? "bg-brand-amber text-white"
                  : "text-brand-muted hover:text-brand-dark hover:bg-brand-surface"
              }`}
            >
              {t.label}
              {t.count > 0 && (
                <span className={`ml-1.5 text-xs ${tab === t.key ? "text-white/70" : "text-brand-muted/60"}`}>
                  ({t.count})
                </span>
              )}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-20">
            <div className="w-6 h-6 border-2 border-brand-amber border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-brand-muted text-sm">Loading...</p>
          </div>
        ) : (
          <>
            {/* ─── Results Tab ─── */}
            {tab === "results" && (
              <div className="space-y-3">
                {results.length === 0 ? (
                  <div className="bg-white border border-brand-border border-dashed rounded-2xl py-16 text-center shadow-card">
                    <p className="text-brand-muted font-display text-lg mb-2">No results yet</p>
                    <p className="text-brand-muted/60 text-sm">Complete an assessment to see your scores here</p>
                  </div>
                ) : (
                  results.map((r) => (
                    <div key={r.candidate_id} className="bg-white border border-brand-border rounded-xl overflow-hidden shadow-card">
                      <div
                        className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-brand-surface/50 transition-colors"
                        onClick={() => setExpanded(expanded === r.candidate_id ? null : r.candidate_id)}
                      >
                        {/* Score circle */}
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center font-mono font-700 text-sm flex-shrink-0 ${
                          r.passed ? "bg-emerald-50 text-emerald-700 border-2 border-emerald-200" : "bg-red-50 text-red-600 border-2 border-red-200"
                        }`}>
                          {r.total_score?.toFixed(0)}%
                        </div>

                        <div className="flex-1 min-w-0">
                          <p className="text-brand-dark font-600 text-sm">{r.assessment_title}</p>
                          <p className="text-brand-muted text-xs">{r.org_name}</p>
                        </div>

                        <div className="text-right">
                          {r.passed ? (
                            <span className="text-xs px-2.5 py-1 rounded-full font-600 bg-emerald-50 text-emerald-700 border border-emerald-200">Passed</span>
                          ) : (
                            <span className="text-xs px-2.5 py-1 rounded-full font-600 bg-red-50 text-red-600 border border-red-200">Not passed</span>
                          )}
                          {r.rank && (
                            <p className="text-brand-muted text-xs mt-1">Rank #{r.rank}</p>
                          )}
                        </div>

                        <span className="text-brand-muted text-xs">{expanded === r.candidate_id ? "\u25B2" : "\u25BC"}</span>
                      </div>

                      {expanded === r.candidate_id && r.scores_by_test && (
                        <div className="border-t border-brand-border px-5 py-4 bg-brand-surface/50">
                          <div className="grid grid-cols-2 gap-3">
                            {Object.entries(r.scores_by_test).map(([key, data]) => (
                              <div key={key} className="bg-white rounded-lg p-3 border border-brand-border">
                                <p className="text-brand-muted text-xs mb-1">{key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</p>
                                <p className="font-mono text-brand-dark text-lg font-600">{data.percentage?.toFixed(0)}%</p>
                                <div className="flex items-center gap-2 mt-1">
                                  <ScoreBadge label={data.label} />
                                  <span className="text-brand-muted text-xs">{data.raw_score}/{data.total_questions}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                          <p className="text-brand-muted text-xs mt-3">Scored: {formatDate(r.scored_at)}</p>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}

            {/* ─── Certificates Tab ─── */}
            {tab === "certificates" && (
              <div className="space-y-3">
                {certs.length === 0 ? (
                  <div className="bg-white border border-brand-border border-dashed rounded-2xl py-16 text-center shadow-card">
                    <p className="text-brand-muted font-display text-lg mb-2">No certificates yet</p>
                    <p className="text-brand-muted/60 text-sm">Pass an assessment with 60%+ to earn a certificate</p>
                  </div>
                ) : (
                  certs.map((cert) => (
                    <div key={cert.id} className="bg-white border border-brand-border rounded-xl p-5 shadow-card">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="text-brand-dark font-600">{cert.test_label}</p>
                          <p className="text-brand-muted text-xs mt-0.5">#{cert.certificate_number}</p>
                        </div>
                        <span className={`text-xs px-2.5 py-1 rounded-full font-600 border ${
                          cert.performance_label === "Excellent" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                          cert.performance_label === "Very Good" ? "bg-blue-50 text-blue-700 border-blue-200" :
                          "bg-amber-50 text-amber-700 border-amber-200"
                        }`}>
                          {cert.performance_label}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 mb-4">
                        <div>
                          <p className="text-brand-muted text-xs">Score</p>
                          <p className="font-mono text-brand-dark font-700 text-xl">{cert.score_percentage.toFixed(0)}%</p>
                        </div>
                        <div>
                          <p className="text-brand-muted text-xs">Issued</p>
                          <p className="text-brand-dark text-sm">{formatDate(cert.issued_at)}</p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <Link
                          href={`/verify/${cert.certificate_number}`}
                          className="flex-1 text-center bg-brand-surface border border-brand-border text-brand-dark text-sm font-600 py-2 rounded-lg hover:bg-brand-border transition-colors"
                        >
                          View Certificate
                        </Link>
                        <button
                          onClick={() => copyLink(cert.verify_url)}
                          className="flex-1 text-center bg-brand-amber text-white text-sm font-600 py-2 rounded-lg hover:bg-brand-amber/90 transition-colors"
                        >
                          Copy Share Link
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* ─── Tests Tab ─── */}
            {tab === "tests" && (
              <div className="space-y-3">
                {tests.map((test) => (
                  <div key={test.key} className="bg-white border border-brand-border rounded-xl p-5 shadow-card hover:shadow-card-hover transition-shadow">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-brand-dark font-600">{test.label}</p>
                        <p className="text-brand-muted text-sm mt-0.5">{test.description}</p>
                      </div>
                      <span className="text-brand-amber font-mono font-700 text-lg whitespace-nowrap ml-4">
                        {test.price_etb} ETB
                      </span>
                    </div>
                    <div className="flex gap-4 mt-3 pt-3 border-t border-brand-border">
                      <div className="flex items-center gap-1.5">
                        <span className="text-brand-muted text-xs">Questions:</span>
                        <span className="text-brand-dark text-xs font-mono font-600">{test.question_count}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-brand-muted text-xs">Time:</span>
                        <span className="text-brand-dark text-xs font-mono font-600">{test.time_limit_minutes} min</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
