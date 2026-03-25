"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { assessmentsApi } from "@/lib/api";

type AvailableTest = { key: string; label: string; description: string };

type TestSelection = {
  test_key: string;
  weight: number;
  time_limit_minutes: number;
};

export default function NewAssessmentPage() {
  const router = useRouter();
  const [tests, setTests] = useState<AvailableTest[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<TestSelection[]>([]);
  const [totalTime, setTotalTime] = useState(60);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    assessmentsApi.listTests().then((res) => setTests(res.data));
  }, []);

  const toggleTest = (key: string) => {
    if (selected.find((s) => s.test_key === key)) {
      setSelected(selected.filter((s) => s.test_key !== key));
    } else {
      setSelected([...selected, { test_key: key, weight: 1, time_limit_minutes: 20 }]);
    }
  };

  const updateSelection = (key: string, field: "weight" | "time_limit_minutes", val: number) => {
    setSelected(selected.map((s) => (s.test_key === key ? { ...s, [field]: val } : s)));
  };

  const handleSubmit = async () => {
    if (!title) { toast.error("Add a title"); return; }
    if (selected.length === 0) { toast.error("Select at least one test"); return; }

    setLoading(true);
    try {
      const res = await assessmentsApi.create({
        title,
        description,
        test_config: selected,
        total_time_limit_minutes: totalTime,
      });
      toast.success("Assessment created");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-surface">
      <nav className="bg-white border-b border-brand-border px-8 py-4 flex items-center gap-4 shadow-card">
        <Link href="/dashboard" className="text-brand-muted text-sm hover:text-brand-dark transition-colors">&larr; Back</Link>
        <span className="text-brand-border">|</span>
        <span className="font-display text-sm font-700 text-brand-dark">New Assessment</span>
      </nav>

      <main className="max-w-3xl mx-auto px-8 py-10">
        <h1 className="font-display text-3xl font-800 text-brand-dark mb-8">Build your assessment</h1>

        {/* Basic info */}
        <section className="mb-8">
          <h2 className="text-brand-muted text-xs uppercase tracking-widest font-600 mb-4">Assessment Details</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-brand-dark text-sm font-500 mb-2">Title *</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Branch Teller Assessment Q3 2025"
                className="w-full bg-white border border-brand-border rounded-lg px-4 py-3 text-brand-dark placeholder:text-brand-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-amber/30 focus:border-brand-amber transition-all shadow-card"
              />
            </div>
            <div>
              <label className="block text-brand-dark text-sm font-500 mb-2">Description (optional)</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Internal notes about this assessment"
                className="w-full bg-white border border-brand-border rounded-lg px-4 py-3 text-brand-dark placeholder:text-brand-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-amber/30 focus:border-brand-amber transition-all resize-none shadow-card"
              />
            </div>
            <div>
              <label className="block text-brand-dark text-sm font-500 mb-2">Total time limit (minutes)</label>
              <input
                type="number"
                value={totalTime}
                onChange={(e) => setTotalTime(Number(e.target.value))}
                className="w-32 bg-white border border-brand-border rounded-lg px-4 py-3 text-brand-dark focus:outline-none focus:ring-2 focus:ring-brand-amber/30 focus:border-brand-amber transition-all font-mono shadow-card"
              />
            </div>
          </div>
        </section>

        {/* Test selection */}
        <section className="mb-10">
          <h2 className="text-brand-muted text-xs uppercase tracking-widest font-600 mb-4">
            Select Tests ({selected.length} selected)
          </h2>
          <div className="space-y-3">
            {tests.map((test) => {
              const sel = selected.find((s) => s.test_key === test.key);
              return (
                <div
                  key={test.key}
                  className={`border rounded-xl p-4 transition-all shadow-card ${
                    sel ? "border-brand-amber bg-brand-amber-light" : "border-brand-border bg-white hover:shadow-card-hover"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <span className="text-brand-dark font-600 text-sm">{test.label}</span>
                      <p className="text-brand-muted text-xs mt-0.5">{test.description}</p>
                    </div>
                    <button
                      onClick={() => toggleTest(test.key)}
                      className={`text-xs font-700 px-3 py-1.5 rounded-lg transition-colors ${
                        sel
                          ? "bg-brand-amber text-white"
                          : "bg-brand-surface text-brand-muted border border-brand-border hover:bg-brand-border"
                      }`}
                    >
                      {sel ? "Selected" : "Add"}
                    </button>
                  </div>
                  {sel && (
                    <div className="flex gap-6 mt-3 pt-3 border-t border-brand-amber/20">
                      <div>
                        <label className="text-brand-muted text-xs">Weight</label>
                        <input
                          type="number"
                          min={1}
                          max={5}
                          value={sel.weight}
                          onChange={(e) => updateSelection(test.key, "weight", Number(e.target.value))}
                          className="ml-2 w-14 bg-white border border-brand-border rounded px-2 py-1 text-brand-dark text-xs font-mono focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-brand-muted text-xs">Minutes</label>
                        <input
                          type="number"
                          min={5}
                          max={60}
                          value={sel.time_limit_minutes}
                          onChange={(e) => updateSelection(test.key, "time_limit_minutes", Number(e.target.value))}
                          className="ml-2 w-16 bg-white border border-brand-border rounded px-2 py-1 text-brand-dark text-xs font-mono focus:outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full bg-brand-amber text-white font-display font-700 py-4 rounded-xl hover:bg-brand-amber/90 transition-colors disabled:opacity-60 text-lg shadow-card"
        >
          {loading ? "Creating..." : "Create Assessment"}
        </button>
      </main>
    </div>
  );
}
