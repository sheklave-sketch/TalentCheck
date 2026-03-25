"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { candidatesApi } from "@/lib/api";

type CandidateRow = { full_name: string; email: string; phone: string };

export default function InvitePage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<CandidateRow[]>([{ full_name: "", email: "", phone: "" }]);
  const [loading, setLoading] = useState(false);

  const addRow = () => setRows([...rows, { full_name: "", email: "", phone: "" }]);
  const removeRow = (i: number) => setRows(rows.filter((_, idx) => idx !== i));
  const updateRow = (i: number, field: keyof CandidateRow, val: string) => {
    const next = [...rows];
    next[i][field] = val;
    setRows(next);
  };

  const handleInvite = async () => {
    const valid = rows.filter((r) => r.full_name && r.email);
    if (valid.length === 0) { toast.error("Add at least one candidate with name and email"); return; }
    setLoading(true);
    try {
      const res = await candidatesApi.invite({ assessment_id: id, candidates: valid });
      toast.success(`${res.data.invited} invitation(s) sent`);
      setRows([{ full_name: "", email: "", phone: "" }]);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to invite");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-surface">
      <nav className="bg-white border-b border-brand-border px-8 py-4 flex items-center gap-4 shadow-card">
        <Link href="/dashboard" className="text-brand-muted text-sm hover:text-brand-dark transition-colors">&larr; Dashboard</Link>
        <span className="text-brand-border">|</span>
        <span className="font-display text-sm font-700 text-brand-dark">Invite Candidates</span>
      </nav>

      <main className="max-w-4xl mx-auto px-8 py-10">
        <h1 className="font-display text-3xl font-800 text-brand-dark mb-2">Send Invitations</h1>
        <p className="text-brand-muted text-sm mb-8">Candidates will receive a unique link via email (and SMS if phone provided)</p>

        {/* Table */}
        <div className="bg-white border border-brand-border rounded-xl overflow-hidden mb-6 shadow-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-brand-border bg-brand-surface/50">
                <th className="text-left text-brand-muted text-xs uppercase tracking-wider px-4 py-3">#</th>
                <th className="text-left text-brand-muted text-xs uppercase tracking-wider px-4 py-3">Full Name *</th>
                <th className="text-left text-brand-muted text-xs uppercase tracking-wider px-4 py-3">Email *</th>
                <th className="text-left text-brand-muted text-xs uppercase tracking-wider px-4 py-3">Phone (optional)</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-brand-border/50">
                  <td className="px-4 py-2 text-brand-muted text-sm font-mono">{i + 1}</td>
                  {(["full_name", "email", "phone"] as const).map((field) => (
                    <td key={field} className="px-2 py-2">
                      <input
                        value={row[field]}
                        onChange={(e) => updateRow(i, field, e.target.value)}
                        placeholder={field === "full_name" ? "Abebe Girma" : field === "email" ? "abebe@email.com" : "+251..."}
                        className="w-full bg-brand-surface border border-transparent rounded-lg px-3 py-2 text-brand-dark text-sm placeholder:text-brand-muted/40 focus:outline-none focus:border-brand-border focus:bg-white transition-all"
                      />
                    </td>
                  ))}
                  <td className="px-4 py-2">
                    <button onClick={() => removeRow(i)} className="text-brand-muted/40 hover:text-red-500 transition-colors text-sm">&times;</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between">
          <button onClick={addRow} className="text-brand-amber text-sm font-600 hover:underline">+ Add row</button>
          <button
            onClick={handleInvite}
            disabled={loading}
            className="bg-brand-amber text-white font-display font-700 px-8 py-3 rounded-xl hover:bg-brand-amber/90 transition-colors disabled:opacity-60 shadow-card"
          >
            {loading ? "Sending..." : `Send ${rows.filter((r) => r.email).length} Invitation(s)`}
          </button>
        </div>
      </main>
    </div>
  );
}
