"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderOpen,
  Layers,
  Settings,
  Activity,
  FlaskConical,
  BookOpen,
} from "lucide-react";

const navItems = [
  {
    href: "/",
    label: "Bảng điều khiển",
    icon: LayoutDashboard,
    color: "text-indigo-500",
    bg: "bg-indigo-50",
  },
  {
    href: "/projects",
    label: "Dự án",
    icon: FolderOpen,
    color: "text-amber-500",
    bg: "bg-amber-50",
  },
  {
    href: "/templates",
    label: "Tài nguyên",
    icon: Layers,
    color: "text-emerald-500",
    bg: "bg-emerald-50",
  },
  {
    href: "/labs",
    label: "Phong lab",
    icon: FlaskConical,
    color: "text-violet-500",
    bg: "bg-violet-50",
  },
  {
    href: "/monitor",
    label: "Monitor",
    icon: Activity,
    color: "text-rose-500",
    bg: "bg-rose-50",
  },
  {
    href: "/guide",
    label: "Hướng dẫn",
    icon: BookOpen,
    color: "text-sky-500",
    bg: "bg-sky-50",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-16 lg:w-60 bg-white border-r border-gray-100 flex flex-col z-50 transition-all duration-200">
      {/* Logo */}
      <div className="px-2 lg:px-5 py-6 border-b border-gray-100">
        <Link href="/" className="flex items-center gap-3 justify-center lg:justify-start">
          <img src="/favicon.svg" alt="Minh Bi Youtube" className="w-10 h-10 rounded-full shadow-md flex-shrink-0" />
          <div className="hidden lg:block">
            <h1 className="text-[15px] font-bold text-gray-800 tracking-tight">Minh Bi Youtube</h1>
            <p className="text-[11px] text-gray-400 font-medium">Video Factory</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 lg:px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={`flex items-center gap-3 px-1.5 lg:px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all justify-center lg:justify-start ${
                isActive
                  ? "bg-indigo-50 text-indigo-600"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  isActive ? "bg-indigo-100" : item.bg
                }`}
              >
                <Icon
                  className={`w-[18px] h-[18px] ${
                    isActive ? "text-indigo-600" : item.color
                  }`}
                />
              </div>
              <span className="hidden lg:inline">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-2 lg:px-3 py-4 border-t border-gray-100">
        <Link
          href="/settings"
          title="Cài đặt"
          className={`flex items-center gap-3 px-1.5 lg:px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all w-full justify-center lg:justify-start ${
            pathname.startsWith("/settings")
              ? "bg-indigo-50 text-indigo-600"
              : "text-gray-400 hover:bg-gray-50 hover:text-gray-600"
          }`}
        >
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
            pathname.startsWith("/settings") ? "bg-indigo-100" : "bg-gray-50"
          }`}>
            <Settings className={`w-[18px] h-[18px] ${
              pathname.startsWith("/settings") ? "text-indigo-600" : "text-gray-400"
            }`} />
          </div>
          <span className="hidden lg:inline">Cài đặt</span>
        </Link>
      </div>
    </aside>
  );
}
