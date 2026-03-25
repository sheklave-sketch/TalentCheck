"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

interface CertificateData {
  valid: boolean;
  certificate_number: string;
  candidate_name: string | null;
  test_label: string | null;
  score_percentage: number | null;
  performance_label: string | null;
  issued_at: string | null;
}

export default function VerifyCertificatePage() {
  const params = useParams();
  const number = params.number as string;
  const [data, setData] = useState<CertificateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!number) return;
    api
      .get(`/api/certificates/verify/${number}`)
      .then((res) => setData(res.data))
      .catch(() => setError("Unable to verify certificate. Please try again later."))
      .finally(() => setLoading(false));
  }, [number]);

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <div className="min-h-screen bg-[#0A0E1A] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-[#F5A623] font-bold text-2xl tracking-wider">
            TALENTCHECK
          </h1>
          <p className="text-gray-400 text-sm mt-1 tracking-widest">
            E T H I O P I A
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#1A1F2E] rounded-2xl border border-[#2A2F3E] shadow-2xl overflow-hidden">
          {/* Top accent bar */}
          <div className="h-1 bg-gradient-to-r from-[#F5A623] via-[#FFC857] to-[#F5A623]" />

          <div className="p-8">
            {loading && (
              <div className="flex flex-col items-center py-12">
                <div className="w-8 h-8 border-2 border-[#F5A623] border-t-transparent rounded-full animate-spin" />
                <p className="text-gray-400 mt-4 text-sm">
                  Verifying certificate...
                </p>
              </div>
            )}

            {error && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-red-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <p className="text-red-400 font-medium">{error}</p>
              </div>
            )}

            {data && !loading && (
              <>
                {/* Status badge */}
                <div className="flex justify-center mb-6">
                  {data.valid ? (
                    <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/30 rounded-full px-6 py-3">
                      <svg
                        className="w-6 h-6 text-emerald-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <span className="text-emerald-400 font-semibold text-lg">
                        Valid Certificate
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-full px-6 py-3">
                      <svg
                        className="w-6 h-6 text-red-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <span className="text-red-400 font-semibold text-lg">
                        Invalid Certificate
                      </span>
                    </div>
                  )}
                </div>

                {/* Certificate number */}
                <div className="text-center mb-6">
                  <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">
                    Certificate Number
                  </p>
                  <p className="text-white font-mono text-lg font-semibold">
                    {data.certificate_number}
                  </p>
                </div>

                {data.valid && (
                  <>
                    {/* Divider */}
                    <div className="border-t border-[#2A2F3E] my-6" />

                    {/* Details grid */}
                    <div className="space-y-4">
                      <div className="flex justify-between items-start">
                        <span className="text-gray-500 text-sm">
                          Candidate
                        </span>
                        <span className="text-white font-semibold text-right">
                          {data.candidate_name}
                        </span>
                      </div>

                      <div className="flex justify-between items-start">
                        <span className="text-gray-500 text-sm">
                          Assessment
                        </span>
                        <span className="text-white font-medium text-right">
                          {data.test_label}
                        </span>
                      </div>

                      <div className="flex justify-between items-center">
                        <span className="text-gray-500 text-sm">Score</span>
                        <span className="text-[#F5A623] font-bold text-xl">
                          {data.score_percentage?.toFixed(0)}%
                        </span>
                      </div>

                      <div className="flex justify-between items-center">
                        <span className="text-gray-500 text-sm">
                          Performance
                        </span>
                        <span
                          className={`font-semibold px-3 py-1 rounded-full text-sm ${
                            data.performance_label === "Excellent"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : data.performance_label === "Very Good"
                              ? "bg-blue-500/20 text-blue-400"
                              : data.performance_label === "Good"
                              ? "bg-amber-500/20 text-amber-400"
                              : "bg-gray-500/20 text-gray-400"
                          }`}
                        >
                          {data.performance_label}
                        </span>
                      </div>

                      <div className="flex justify-between items-start">
                        <span className="text-gray-500 text-sm">
                          Date Issued
                        </span>
                        <span className="text-white text-sm">
                          {formatDate(data.issued_at)}
                        </span>
                      </div>
                    </div>
                  </>
                )}

                {!data.valid && (
                  <p className="text-center text-gray-400 text-sm mt-4">
                    This certificate number was not found in our records. Please
                    check the number and try again.
                  </p>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="bg-[#141824] px-8 py-4 text-center">
            <p className="text-gray-500 text-xs">
              Issued by TalentCheck Ethiopia &mdash; Verified{" "}
              {new Date().toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
