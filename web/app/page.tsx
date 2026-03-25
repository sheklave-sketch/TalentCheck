"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const token = localStorage.getItem("tc_token");
    router.replace(token ? "/dashboard" : "/login");
  }, [router]);

  return (
    <div className="min-h-screen bg-brand-surface flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-brand-amber border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
