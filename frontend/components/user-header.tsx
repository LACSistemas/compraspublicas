"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ROTAS_SEM_HEADER = ["/login", "/register", "/aguardando"];

export function UserHeader() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();

  if (loading || ROTAS_SEM_HEADER.includes(pathname)) return null;
  if (!user) return null;

  return (
    <header className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 px-6 py-3 text-sm">
      <span className="font-medium text-gray-700 dark:text-gray-300">
        {user.nome}
        <span className="ml-2 text-gray-400 font-normal">{user.email}</span>
      </span>
      <div className="flex items-center gap-4">
        {user.is_owner && (
          <Link href="/admin" className="text-blue-600 hover:underline">
            Admin
          </Link>
        )}
        <button
          onClick={logout}
          className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Sair
        </button>
      </div>
    </header>
  );
}
