"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const tgId = searchParams.get("tg_id");

    // Telegram auto-login: ?tg_id=123456
    if (tgId) {
      api.post("/api/auth/telegram-login", { telegram_id: Number(tgId) })
        .then((res) => {
          localStorage.setItem("tc_token", res.data.access_token);
          router.replace("/dashboard");
        })
        .catch(() => {
          router.replace("/login");
        });
      return;
    }

    // Normal flow
    const token = localStorage.getItem("tc_token");
    router.replace(token ? "/dashboard" : "/login");
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
