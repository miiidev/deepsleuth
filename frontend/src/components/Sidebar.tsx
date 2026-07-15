import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { Scan, Clock, Info, FileText, Menu, X } from "lucide-react";
import { getMetrics } from "../api/client";

const navItems = [
  { to: "/upload", label: "Analyze", icon: Scan },
  { to: "/history", label: "History", icon: Clock },
  { to: "/about", label: "About", icon: Info },
  { to: "/methodology", label: "Methodology", icon: FileText },
];

export default function Sidebar() {
  const location = useLocation();
  const [version, setVersion] = useState("v0.1.0");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    getMetrics()
      .then((m: { version: string }) => setVersion(`v${m.version}`))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [mobileOpen]);

  const isActive = (to: string) => {
    if (to === "/upload") {
      return ["/upload", "/processing", "/results"].some((p) =>
        location.pathname.startsWith(p)
      );
    }
    return location.pathname === to;
  };

  const navList = (
    <>
      <nav className="flex-1 flex flex-col gap-1 px-4 py-8">
        {navItems.map((item) => {
          const active = isActive(item.to);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`group flex items-center gap-3 px-3 py-2.5 text-sm font-mono rounded-md transition-all duration-200 no-underline ${
                active
                  ? "text-neon neon-glow-sm bg-[#00FF41]/5"
                  : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.03]"
              }`}
            >
              <Icon
                size={16}
                className={
                  active
                    ? "text-neon"
                    : "text-gray-600 group-hover:text-gray-400 transition-colors duration-200"
                }
              />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-4 py-4 border-t border-[#1F1F1F]">
        <span className="text-xs font-mono text-gray-600">
          DeepSleuth {version}
        </span>
      </div>
    </>
  );

  return (
    <>
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-40 md:hidden w-10 h-10 flex items-center justify-center rounded-md bg-[#0A0A0A] border border-[#1F1F1F] text-gray-400 hover:text-neon transition-colors"
        aria-label="Open navigation"
      >
        <Menu size={18} />
      </button>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="sidebar-enter absolute inset-y-0 left-0 w-[240px] bg-[#0A0A0A] border-r border-[#1F1F1F] flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#1F1F1F]">
              <span className="text-xs font-mono text-gray-500">NAV</span>
              <button
                onClick={() => setMobileOpen(false)}
                className="text-gray-500 hover:text-neon transition-colors"
                aria-label="Close navigation"
              >
                <X size={18} />
              </button>
            </div>
            {navList}
          </aside>
        </div>
      )}

      <aside className="hidden md:flex md:w-[200px] lg:w-[220px] h-screen sticky top-0 bg-[#0A0A0A] border-r border-[#1F1F1F] flex-col flex-shrink-0">
        {navList}
      </aside>
    </>
  );
}
