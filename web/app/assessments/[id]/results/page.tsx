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
    "Excellent": "bg-[#4ECDC4]/20 text-[#4ECDC4]",
    "Good":      "bg-[#F5A623]/20 text-[#F5A623]",
    "Fair":      "bg-white/10 text-white/60",
    "Below Average": "bg-red-500/20 text-red-400",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-600 ${colors[label] || "bg-white/10 text-white/40"}`}>
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
    <div className="min-h-screen bg-[#0A0E1A]">
      <nav className="border-b border-white/10 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-white/40 text-sm hover:text-white/70">← Dashboard</Link>
          <span className="text-white/20">|</span>
          <span className="font-display text-sm font-700 text-white">Results</span>
        </div>
        <div className="flex gap-3">
          <button
            onClick={runScoring}
            disabled={scoring}
            className="border border-[#4ECDC4]/40 text-[#4ECDC4] text-sm px-4 py-2 rounded-lg hover:bg-[#4ECDC4]/10 transition-colors disabled:opacity-50"
          >
            {scoring ? "Scoring..." : "Run Scoring"}
          </button>
          <button
            onClick={exportExcel}
            className="border border-white/20 text-white/70 text-sm px-4 py-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            Export Excel
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-8 py-10">
        <h1 className="font-display text-3xl font-800 text-white mb-8">Candidate Rankings</h1>

        {loading ? (
          <div className="text-white/40 text-center py-20">Loading results...</div>
        ) : results.length === 0 ? (
          <div className="border border-white/10 border-dashed rounded-2xl py-24 text-center">
            <p className="text-white/30 font-display text-lg mb-2">No results yet</p>
            <p className="text-white/20 text-sm mb-6">Once candidates complete their assessments, click "Run Scoring"</p>
            <button
              onClick={runScoring}
              className="bg-[#4ECDC4] text-[#0A0E1A] font-display font-700 text-sm px-6 py-3 rounded-lg hover:opacity-90 transition-opacity"
            >
              Run Scoring Now
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {results.map((r) => (
              <div key={r.candidate_id} className="border border-white/10 rounded-xl overflow-hidden">
                <div
                  className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-white/3 transition-colors"
                  onClick={() => setExpanded(expanded === r.candidate_id ? null : r.candidate_id)}
                >
                  {/* Rank */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-display font-800 text-sm flex-shrink-0 ${
                    r.rank === 1 ? "bg-[#F5A623] text-[#0A0E1A]" :
                    r.rank === 2 ? "bg-white/20 text-white" :
                    r.rank === 3 ? "bg-white/10 text-white/70" : "bg-transparent border border-white/10 text-white/40"
                  }`}>
                    {r.rank}
                  </div>

                  {/* Name */}
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-600 text-sm">{r.full_name}</p>
                    <p className="text-white/40 text-xs">{r.email}</p>
                  </div>

                  {/* Score */}
                  <div className="text-right">
                    <p className="font-mono text-white font-600 text-lg">{r.total_score?.toFixed(1)}%</p>
                    {r.percentile != null && (
                      <p className="text-white/40 text-xs">{r.percentile}th pct.</p>
                    )}
                  </div>

                  {/* Flags */}
                  {r.has_flags && (
                    <span className="text-xs text-orange-400 border border-orange-400/30 px-2 py-0.5 rounded-full">
                      ⚠ Flagged
                    </span>
                  )}

                  {/* PDF */}
                  <button
                    onClick={(e) => { e.stopPropagation(); downloadPdf(r.candidate_id, r.full_name); }}
                    className="text-white/40 text-xs hover:text-white/70 transition-colors"
                  >
                    PDF
                  </button>

                  <span className="text-white/30 text-xs">{expanded === r.candidate_id ? "▲" : "▼"}</span>
                </div>

                {/* Expanded score breakdown */}
                {expanded === r.candidate_id && r.scores_by_test && (
                  <div className="border-t border-white/10 px-5 py-4 bg-white/3">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {Object.entries(r.scores_by_test).map(([key, data]) => (
                        <div key={key} className="bg-white/5 rounded-lg p-3">
                          <p className="text-white/50 text-xs mb-2">{key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</p>
                          <p className="font-mono text-white text-lg font-600">{data.percentage?.toFixed(0)}%</p>
                          <div className="flex items-center gap-2 mt-1">
                            <ScoreBadge label={data.label} />
                            <span className="text-white/30 text-xs">{data.raw_score}/{data.total_questions}</span>
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
