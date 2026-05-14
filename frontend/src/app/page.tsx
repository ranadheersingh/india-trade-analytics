"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const t = typeof window !== "undefined" ? localStorage.getItem("trade_token") : null;
    router.replace(t ? "/dashboards/executive" : "/login");
  }, [router]);
  return (
    <div className="min-h-screen flex items-center justify-center text-brand-600">
      Loading…
    </div>
  );
}
