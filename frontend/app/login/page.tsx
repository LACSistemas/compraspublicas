"use client";

import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

function AuthLogo() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-bold tracking-tight select-none">
        LA
      </span>
      <span className="font-bold text-lg tracking-tight text-foreground">
        Licita<span className="text-primary">AI</span>
      </span>
    </div>
  );
}

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao fazer login";
      if (msg.toLowerCase().includes("aguardando")) {
        router.push("/aguardando");
      } else {
        setErro(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Painel lateral de marca */}
      <div className="hidden lg:flex lg:w-2/5 bg-primary flex-col justify-between p-12">
        <div className="flex items-center gap-2.5">
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary-foreground/10 text-primary-foreground text-sm font-bold tracking-tight">
            LA
          </span>
          <span className="font-bold text-lg text-primary-foreground tracking-tight">LicitaAI</span>
        </div>
        <div className="space-y-4">
          <h2 className="text-3xl font-bold text-primary-foreground leading-snug">
            Auditoria inteligente de compras públicas
          </h2>
          <p className="text-primary-foreground/70 text-sm leading-relaxed">
            Pesquise processos licitatórios, analise documentos com IA e gere ETP e TR automaticamente.
          </p>
        </div>
        <p className="text-primary-foreground/40 text-xs">© 2026 LicitaAI</p>
      </div>

      {/* Formulário */}
      <div className="flex flex-1 items-center justify-center bg-background px-6 py-12">
        <div className="w-full max-w-sm space-y-8">
          <div className="lg:hidden">
            <AuthLogo />
          </div>

          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">Entrar na conta</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Não tem conta?{" "}
              <Link href="/register" className="text-primary font-medium hover:underline">
                Criar conta
              </Link>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="email">
                E-mail
              </label>
              <Input
                id="email"
                type="email"
                required
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-10"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="password">
                Senha
              </label>
              <Input
                id="password"
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-10"
              />
            </div>

            {erro && (
              <p className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">{erro}</p>
            )}

            <Button
              type="submit"
              disabled={loading}
              size="lg"
              className="w-full h-10 font-semibold"
            >
              {loading ? "Entrando..." : "Entrar"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
