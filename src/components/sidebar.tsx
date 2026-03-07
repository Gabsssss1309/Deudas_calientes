"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { UserRole } from "@/types/database";

interface SidebarProps {
  user: {
    nombre: string;
    email: string;
    rol: UserRole;
  };
}

const navItems = [
  {
    label: "Dashboard",
    href: "/app",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    label: "Compromisos",
    href: "/app/compromisos",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  },
  {
    label: "Financiero",
    href: "/app/financiero",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

const adminItems = [
  {
    label: "Usuarios",
    href: "/app/admin/usuarios",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    ),
  },
];

export function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/app") return pathname === "/app";
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-64 bg-unergy-deep-purple border-r border-white/10 flex flex-col h-full">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <h1 className="font-display text-xl font-bold text-unergy-cream">
          Debt Tracker
        </h1>
        <p className="text-xs text-unergy-purple mt-0.5 font-semibold">
          by Unergy
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3 px-3">
          Modulos
        </p>
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
              isActive(item.href)
                ? "bg-unergy-purple/20 text-unergy-cream font-semibold"
                : "text-gray-400 hover:text-unergy-cream hover:bg-white/5"
            }`}
          >
            {item.icon}
            {item.label}
          </Link>
        ))}

        {user.rol === "admin" && (
          <>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3 mt-6 px-3">
              Admin
            </p>
            {adminItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive(item.href)
                    ? "bg-unergy-purple/20 text-unergy-cream font-semibold"
                    : "text-gray-400 hover:text-unergy-cream hover:bg-white/5"
                }`}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
          </>
        )}
      </nav>

      {/* User info */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-unergy-purple/30 flex items-center justify-center text-unergy-cream text-sm font-bold">
            {(user.nombre || user.email).charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-unergy-cream truncate">
              {user.nombre || user.email}
            </p>
            <p className="text-xs text-gray-500 truncate">{user.rol}</p>
          </div>
        </div>
        <form action="/auth/signout" method="post" className="mt-3">
          <button
            type="submit"
            className="text-xs text-gray-500 hover:text-unergy-cream transition-colors"
          >
            Cerrar sesion
          </button>
        </form>
      </div>
    </aside>
  );
}
