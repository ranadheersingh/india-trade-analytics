"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LayoutDashboard, Globe, MapPin, Boxes, Settings, LogOut, TrendingUp } from "lucide-react";
import { getMe, logout } from "@/lib/api";

const links = [
  { href: "/dashboards/executive", label: "Executive Overview", icon: LayoutDashboard },
  { href: "/dashboards/country",   label: "Country Analysis",   icon: Globe },
  { href: "/dashboards/states",    label: "State Performance",  icon: MapPin },
  { href: "/dashboards/sector",    label: "Sector Deep-dive",   icon: Boxes },
  { href: "/admin",                label: "Admin",              icon: Settings },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const t = typeof window !== "undefined" ? localStorage.getItem("trade_token") : null;
    if (!t) {
      router.replace("/login");
      return;
    }
    getMe().then(setUser).catch(() => {
      router.replace("/login");
    });
  }, [router]);

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center text-brand-600">
        Loading…
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-brand-700 text-white flex flex-col">
        <div className="px-6 py-5 flex items-center gap-2 border-b border-brand-600">
          <div className="w-9 h-9 rounded-lg bg-white/10 flex items-center justify-center">
            <TrendingUp size={18} />
          </div>
          <div>
            <div className="font-semibold">India Trade</div>
            <div className="text-xs text-brand-200">Analytics</div>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {links
            .filter(l => l.href !== "/admin" || user.role === "admin")
            .map(({ href, label, icon: Icon }) => {
              const active = pathname?.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                    active ? "bg-white/15 text-white" : "text-brand-100 hover:bg-white/5"
                  }`}
                >
                  <Icon size={16} /> {label}
                </Link>
              );
            })}
        </nav>
        <div className="p-3 border-t border-brand-600">
          <div className="px-3 py-2 text-sm">
            <div className="font-medium truncate">{user.full_name || user.email}</div>
            <div className="text-xs text-brand-200">{user.role}</div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-brand-100 hover:bg-white/5"
          >
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
