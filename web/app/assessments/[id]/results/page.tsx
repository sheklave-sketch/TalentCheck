"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { resultsApi, candidatesApi, assessmentsApi } from "@/lib/api";

type Result = {
  rank: number;
  candidate_id: string;
  full_name: string;
  email: string;
  total_score: number;
  percentile: number;
  scores_by_test: Record<string, { percentage: number; label: string; raw_score: number; total_questions: number }>;
  has_flags: boolean;
  pdf_url: string | null;
};

function ScoreBadge({ label }: { label: string }) {
  const colors: Record<string, string> = {
    "Excellent": "bg-emerald-50 text-emerald-700 border-emerald-200",
    "Good":      "bg-amber-50 text-amber-700 border-amber-200",
    "Fair":      "bg-gray-50 text-gray-600 border-gray-200",
    "Below Average": "bg-red-50 text-red-600 border-red-200",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-600 border ${colors[label] || "bg-gray-50 text-gray-400 border-gray-200"}`}>
      {label}
    </span>
  );
}

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = () => {
    resultsApi.getByAssessment(id)
      .then((res) => setResults(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const runScoring = async () => {
    setScoring(true);
    try {
      const res = await resultsApi.score(id);
      toast.success(`Scored ${res.data.scored} candidate(s)`);
      load();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Scoring failed");
    } finally {
      setScoring(false);
    }
  };

  const exportExcel = async () => {
    try {
      const res = await resultsApi.exportExcel(id);
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `results_${id.slice(0, 8)}.xlsx`;
      a.click();
    } catch {
      toast.error("Export failed");
    }
  };

  const downloadPdf = async (candidateId: string, name: string) => {
    try {
      const res = await resultsApi.downloadPdf(candidateId);
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${name.replace(/ /g, "_")}.pdf`;
      a.click();
    } catch {
      toast.error("PDF generation failed");
    }
  };

  return (
    <div className="min-h-screen bg-brand-surface">
      <nav className="bg-white border-b border-brand-border px-8 py-4 flex items-center justify-between shadow-card">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-brand-muted text-sm hover:text-brand-dark transition-colors">&larr; Dashboard</Link>
          <span className="text-brand-border">|</span>
          <span className="font-display text-sm font-700 text-brand-dark">Results</span>
        </div>
        <div className="flex gap-3">
          <button
            onClick={runScoring}
            disabled={scoring}
            className="border border-brand-teal text-brand-teal text-sm font-600 px-4 py-2 rounded-lg hover:bg-brand-teal-light transition-colors disabled:opacity-50"
          >
            {scoring ? "Scoring..." : "Run Scoring"}
          </button>
          <button
            onClick={exportExcel}
            className="border border-brand-border text-brand-muted text-sm px-4 py-2 rounded-lg hover:bg-brand-surface transition-colors"
          >
            Export Excel
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-8 py-10">
        <h1 className="font-display text-3xl font-800 text-brand-dark mb-8">Candidate Rankings</h1>

        {loading ? (
          <div className="text-brand-muted text-center py-20">Loading results...</div>
        ) : results.length === 0 ? (
          <div className="bg-white border border-brand-border border-dashed rounded-2xl py-24 text-center shadow-card">
            <p className="text-brand-muted font-display text-lg mb-2">No results yet</p>
            <p className="text-brand-muted/60 text-sm mb-6">Once candidates complete their assessments, click &ldquo;Run Scoring&rdquo;</p>
            <button
              onClick={runScoring}
              className="bg-brand-teal text-white font-display font-700 text-sm px-6 py-3 rounded-lg hover:opacity-90 transition-opacity"
            >
              Run Scoring Now
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {results.map((r) => (
              <div key={r.candidate_id} className="bg-white border border-brand-border rounded-xl overflow-hidden shadow-card">
                <div
                  className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-brand-surface/50 transition-colors"
                  onClick={() => setExpanded(expanded === r.candidate_id ? null : r.candidate_id)}
                >
                  {/* Rank */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-display font-800 text-sm flex-shrink-0 ${
                    r.rank === 1 ? "bg-brand-amber text-white" :
                    r.rank === 2 ? "bg-gray-200 text-gray-600" :
                    r.rank === 3 ? "bg-amber-100 text-amber-700" : "bg-brand-surface border border-brand-border text-brand-muted"
                  }`}>
                    {r.rank}
                  </div>

                  {/* Name */}
                  <div className="flex-1 min-w-0">
                    <p className="text-brand-dark font-600 text-sm">{r.full_name}</p>
                    <p className="text-brand-muted text-xs">{r.email}</p>
                  </div>

                  {/* Score */}
                  <div className="text-right">
                    <p className="font-mono text-brand-dark font-600 text-lg">{r.total_score?.toFixed(1)}%</p>
                    {r.percentile != null && (
                      <p className="text-brand-muted text-xs">{r.percentile}th pct.</p>
                    )}
                  </div>

                  {/* Flags */}
                  {r.has_flags && (
                    <span className="text-xs text-orange-600 border border-orange-200 bg-orange-50 px-2 py-0.5 rounded-full font-600">
                      Flagged
                    </span>
                  )}

                  {/* PDF */}
                  <button
                    onClick={(e) => { e.stopPropagation(); downloadPdf(r.candidate_id, r.full_name); }}
                    className="text-brand-muted text-xs hover:text-brand-dark transition-colors"
                  >
                    PDF
                  </button>

                  <span className="text-brand-muted text-xs">{expanded === r.candidate_id ? "\u25B2" : "\u25BC"}</span>
                </div>

                {/* Expanded score breakdown */}
                {expanded === r.candidate_id && r.scores_by_test && (
                  <div className="border-t border-brand-border px-5 py-4 bg-brand-surface/50">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {Object.entries(r.scores_by_test).map(([key, data]) => (
                        <div key={key} className="bg-white rounded-lg p-3 border border-brand-border">
                          <p className="text-brand-muted text-xs mb-2">{key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</p>
                          <p className="font-mono text-brand-dark text-lg font-600">{data.percentage?.toFixed(0)}%</p>
                          <div className="flex items-center gap-2 mt-1">
                            <ScoreBadge label={data.label} />
                            <span className="text-brand-muted text-xs">{data.raw_score}/{data.total_questions}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
