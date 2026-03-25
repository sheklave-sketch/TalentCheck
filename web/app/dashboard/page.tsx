"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { assessmentsApi, resultsApi } from "@/lib/api";
import { toast } from "sonner";

type Assessment = {
  id: string;
  title: string;
  status: string;
  tests: string[];
  candidate_count: number;
  created_at: string;
};

const statusColors: Record<string, string> = {
  draft:    "bg-brand-dark/5 text-brand-muted",
  active:   "bg-brand-teal-light text-brand-teal",
  closed:   "bg-gray-100 text-gray-400",
  archived: "bg-gray-50 text-gray-300",
};

export default function DashboardPage() {
  const router = useRouter();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("tc_token");
    if (!token) { router.push("/login"); return; }

    assessmentsApi.list()
      .then((res) => setAssessments(res.data))
      .catch(() => toast.error("Failed to load assessments"))
      .finally(() => setLoading(false));
  }, [router]);

  const activateAssessment = async (id: string) => {
    try {
      await assessmentsApi.updateStatus(id, "active");
      setAssessments((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: "active" } : a))
      );
      toast.success("Assessment activated");
    } catch {
      toast.error("Failed to activate");
    }
  };

  return (
    <div className="min-h-screen bg-brand-surface">
      {/* Nav */}
      <nav className="bg-white border-b border-brand-border px-8 py-4 flex items-center justify-between shadow-card">
        <span className="font-display text-lg font-800 text-brand-dark tracking-tight">
          Talent<span className="text-brand-amber">Check</span>
        </span>
        <div className="flex items-center gap-4">
          <Link
            href="/assessments/new"
            className="bg-brand-amber text-white font-display font-700 text-sm px-4 py-2 rounded-lg hover:bg-brand-amber/90 transition-colors shadow-card"
          >
            + New Assessment
          </Link>
          <button
            onClick={() => { localStorage.removeItem("tc_token"); router.push("/login"); }}
            className="text-brand-muted text-sm hover:text-brand-dark transition-colors"
          >
            Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="mb-10">
          <h1 className="font-display text-3xl font-800 text-brand-dark mb-1">Assessments</h1>
          <p className="text-brand-muted text-sm">Manage your hiring assessments and view results</p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-10">
          {[
            { label: "Total Assessments", value: assessments.length },
            { label: "Active", value: assessments.filter((a) => a.status === "active").length },
            { label: "Total Candidates", value: assessments.reduce((s, a) => s + a.candidate_count, 0) },
          ].map((stat) => (
            <div key={stat.label} className="bg-white border border-brand-border rounded-xl p-5 shadow-card">
              <p className="font-display text-3xl font-800 text-brand-dark mb-1">{stat.value}</p>
              <p className="text-brand-muted text-sm">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Table */}
        {loading ? (
          <div className="text-brand-muted text-sm py-20 text-center">Loading...</div>
        ) : assessments.length === 0 ? (
          <div className="bg-white border border-brand-border border-dashed rounded-2xl py-24 text-center shadow-card">
            <p className="text-brand-muted font-display text-lg mb-4">No assessments yet</p>
            <Link
              href="/assessments/new"
              className="bg-brand-amber text-white font-display font-700 text-sm px-6 py-3 rounded-lg hover:bg-brand-amber/90 transition-colors"
            >
              Create your first assessment
            </Link>
          </div>
        ) : (
          <div className="bg-white border border-brand-border rounded-xl overflow-hidden shadow-card">
            <table className="w-full">
              <thead>
                <tr className="border-b border-brand-border bg-brand-surface/50">
                  {["Title", "Tests", "Candidates", "Status", ""].map((h) => (
                    <th key={h} className="text-left text-brand-muted text-xs font-600 uppercase tracking-wider px-5 py-3.5">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {assessments.map((a) => (
                  <tr key={a.id} className="border-b border-brand-border/50 hover:bg-brand-surface/50 transition-colors">
                    <td className="px-5 py-4">
                      <p className="text-brand-dark font-600 text-sm">{a.title}</p>
                      <p className="text-brand-muted text-xs mt-0.5 font-mono">{a.id.slice(0, 8)}</p>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-1">
                        {a.tests.slice(0, 3).map((t) => (
                          <span key={t} className="bg-brand-surface text-brand-muted text-xs px-2 py-0.5 rounded-full border border-brand-border">
                            {t.replace("_", " ")}
                          </span>
                        ))}
                        {a.tests.length > 3 && (
                          <span className="text-brand-muted text-xs">+{a.tests.length - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="font-mono text-brand-dark text-sm">{a.candidate_count}</span>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`text-xs px-2.5 py-1 rounded-full font-600 ${statusColors[a.status]}`}>
                        {a.status}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3 justify-end">
                        {a.status === "draft" && (
                          <button
                            onClick={() => activateAssessment(a.id)}
                            className="text-brand-teal text-xs font-600 hover:underline"
                          >
                            Activate
                          </button>
                        )}
                        <Link
                          href={`/assessments/${a.id}/results`}
                          className="text-brand-muted text-xs hover:text-brand-dark transition-colors"
                        >
                          View results &rarr;
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
