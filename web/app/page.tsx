"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const tgId = searchParams.get("tg_id");
    const role = searchParams.get("role");

    // Telegram auto-login: ?tg_id=123456
    if (tgId) {
      // Store telegram_id for candidate dashboard
      localStorage.setItem("tc_tg_id", tgId);

      // If role=candidate, go straight to candidate dashboard
      if (role === "candidate") {
        router.replace("/my");
        return;
      }

      // Try employer login
      api.post("/api/auth/telegram-login", { telegram_id: Number(tgId) })
        .then((res) => {
          localStorage.setItem("tc_token", res.data.access_token);
          router.replace("/dashboard");
        })
        .catch(() => {
          // Not an employer — send to candidate dashboard
          router.replace("/my");
        });
      return;
    }

    // Normal flow
    const token = localStorage.getItem("tc_token");
    if (token) {
      router.replace("/dashboard");
    } else if (localStorage.getItem("tc_tg_id")) {
      router.replace("/my");
    } else {
      router.replace("/login");
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen bg-brand-surface flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-brand-amber border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-surface flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-brand-amber border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <HomeContent />
    </Suspense>
  );
}
