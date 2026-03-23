"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { authApi } from "@/lib/api";

type LoginForm = { email: string; password: string };

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>();

  const onSubmit = async (data: LoginForm) => {
    setLoading(true);
    try {
      const res = await authApi.login(data.email, data.password);
      localStorage.setItem("tc_token", res.data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0E1A] flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-[480px] p-12 border-r border-white/10">
        <div>
          <span className="font-display text-xl font-800 text-white tracking-tight">
            Talent<span className="text-[#F5A623]">Check</span>
          </span>
        </div>
        <div>
          <blockquote className="text-white/70 text-lg font-display leading-relaxed mb-6">
            "We screened 800 applicants in 4 days. TalentCheck gave us a ranked list and we hired the top 12 within a week."
          </blockquote>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#F5A623]/20 flex items-center justify-center">
              <span className="text-[#F5A623] font-display font-700 text-sm">BK</span>
            </div>
            <div>
              <p className="text-white text-sm font-600">Bethlehem K.</p>
              <p className="text-white/50 text-xs">HR Director, Awash Bank</p>
            </div>
          </div>
        </div>
        <div className="flex gap-6">
          {[
            { value: "50%", label: "Faster Hiring" },
            { value: "800+", label: "Candidates Tested" },
            { value: "6", label: "Test Types" },
          ].map((stat) => (
            <div key={stat.label}>
              <p className="font-display text-2xl font-800 text-[#F5A623]">{stat.value}</p>
              <p className="text-white/50 text-xs mt-0.5">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="mb-10 lg:hidden">
            <span className="font-display text-xl font-800 text-white tracking-tight">
              Talent<span className="text-[#F5A623]">Check</span>
            </span>
          </div>

          <h1 className="font-display text-3xl font-800 text-white mb-2">Welcome back</h1>
          <p className="text-white/50 text-sm mb-10">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-[#F5A623] hover:underline">
              Create one
            </Link>
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-white/70 text-sm mb-2">Work email</label>
              <input
                {...register("email", { required: true })}
                type="email"
                placeholder="you@organization.com"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#F5A623]/60 transition-colors"
              />
            </div>
            <div>
              <label className="block text-white/70 text-sm mb-2">Password</label>
              <input
                {...register("password", { required: true })}
                type="password"
                placeholder="••••••••"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#F5A623]/60 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#F5A623] text-[#0A0E1A] font-display font-700 py-3.5 rounded-lg hover:bg-[#F5A623]/90 transition-colors disabled:opacity-60 mt-2"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
