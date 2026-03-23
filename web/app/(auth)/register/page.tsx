"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { authApi } from "@/lib/api";

type RegisterForm = {
  org_name: string;
  full_name: string;
  email: string;
  password: string;
};

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit } = useForm<RegisterForm>();

  const onSubmit = async (data: RegisterForm) => {
    setLoading(true);
    try {
      const res = await authApi.register(data);
      localStorage.setItem("tc_token", res.data.access_token);
      toast.success("Account created! Welcome to TalentCheck.");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0E1A] flex items-center justify-center p-8">
      <div className="w-full max-w-md">
        <div className="mb-10">
          <Link href="/" className="font-display text-xl font-800 text-white tracking-tight">
            Talent<span className="text-[#F5A623]">Check</span>
          </Link>
        </div>

        <h1 className="font-display text-3xl font-800 text-white mb-2">Create your account</h1>
        <p className="text-white/50 text-sm mb-10">
          Already registered?{" "}
          <Link href="/login" className="text-[#F5A623] hover:underline">
            Sign in
          </Link>
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div>
            <label className="block text-white/70 text-sm mb-2">Organization name</label>
            <input
              {...register("org_name", { required: true })}
              placeholder="Awash Bank, MyStartup, etc."
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#F5A623]/60 transition-colors"
            />
          </div>
          <div>
            <label className="block text-white/70 text-sm mb-2">Your full name</label>
            <input
              {...register("full_name", { required: true })}
              placeholder="Abeba Girma"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#F5A623]/60 transition-colors"
            />
          </div>
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
              {...register("password", { required: true, minLength: 8 })}
              type="password"
              placeholder="At least 8 characters"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-[#F5A623]/60 transition-colors"
            />
          </div>

          <div className="bg-white/5 border border-white/10 rounded-lg p-4">
            <p className="text-white/60 text-xs leading-relaxed">
              You&apos;re starting on the <span className="text-[#F5A623]">Starter plan</span> —
              10 candidates/month, 1 active assessment. Upgrade anytime.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#F5A623] text-[#0A0E1A] font-display font-700 py-3.5 rounded-lg hover:bg-[#F5A623]/90 transition-colors disabled:opacity-60"
          >
            {loading ? "Creating account..." : "Get started — it's free"}
          </button>
        </form>
      </div>
    </div>
  );
}
