"use client";

import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { ChevronDown, LogOut, LayoutDashboard, Search, PlusCircle } from "lucide-react";

const ROTAS_SEM_NAV = ["/login", "/register", "/aguardando"];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 shrink-0">
      <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground text-xs font-bold tracking-tight select-none">
        LA
      </span>
      <span className="font-bold text-base tracking-tight text-foreground">
        Licita<span className="text-primary">AI</span>
      </span>
    </Link>
  );
}

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      className={`text-sm font-medium transition-colors px-1 py-0.5 rounded ${
        active
          ? "text-primary"
          : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );
}

function UserMenu({ nome, email, isOwner }: { nome: string; email: string; isOwner: boolean }) {
  const { logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
      >
        <span className="hidden sm:block max-w-[160px] truncate">{nome}</span>
        <ChevronDown className={`size-3.5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1.5 z-50 min-w-[200px] rounded-xl border border-border bg-card shadow-lg py-1.5 animate-in fade-in-0 zoom-in-95">
          <div className="px-3 py-2 border-b border-border mb-1">
            <p className="text-xs font-medium text-foreground truncate">{nome}</p>
            <p className="text-xs text-muted-foreground truncate">{email}</p>
          </div>
          {isOwner && (
            <button
              onClick={() => { setOpen(false); router.push("/admin"); }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
            >
              <LayoutDashboard className="size-4 text-muted-foreground" />
              Painel Admin
            </button>
          )}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors"
          >
            <LogOut className="size-4" />
            Sair
          </button>
        </div>
      )}
    </div>
  );
}

export function Navbar() {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  if (loading || ROTAS_SEM_NAV.includes(pathname)) return null;
  if (!user) return null;

  const isActive = (path: string) => pathname === path || pathname.startsWith(path + "/");

  return (
    <header className="sticky top-0 z-40 h-14 bg-card border-b border-border">
      <div className="max-w-6xl mx-auto h-full flex items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Logo />
          {user.is_active && (
            <nav className="hidden sm:flex items-center gap-1">
              <NavLink href="/pesquisas" label="Pesquisas" active={isActive("/pesquisas")} />
              <NavLink href="/nova-pesquisa" label="Nova pesquisa" active={isActive("/nova-pesquisa")} />
              <NavLink href="/contratacoes" label="Contratações" active={isActive("/contratacoes")} />
            </nav>
          )}
        </div>

        <div className="flex items-center gap-3">
          {user.is_active && (
            <Link
              href="/nova-pesquisa"
              className="hidden sm:flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <PlusCircle className="size-3.5" />
              Nova pesquisa
            </Link>
          )}
          <UserMenu nome={user.nome} email={user.email} isOwner={user.is_owner} />
        </div>
      </div>
    </header>
  );
}
