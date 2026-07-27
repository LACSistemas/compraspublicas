"use client";

import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setLoading(true);
    try {
      await register(nome, email, password);
      router.push("/aguardando");
    } catch (err: unknown) {
      setErro(err instanceof Error ? err.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Painel lateral */}
      <div className="hidden lg:flex lg:w-2/5 bg-primary flex-col justify-between p-12">
        <div className="flex items-center gap-2.5">
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary-foreground/10 text-primary-foreground text-sm font-bold tracking-tight">
            LA
          </span>
          <span className="font-bold text-lg text-primary-foreground tracking-tight">LicitaAI</span>
        </div>
        <div className="space-y-4">
          <h2 className="text-3xl font-bold text-primary-foreground leading-snug">
            Comece a auditar com inteligência artificial
          </h2>
          <p className="text-primary-foreground/70 text-sm leading-relaxed">
            Após o cadastro, seu acesso será aprovado pelo administrador. Você receberá acesso completo ao sistema.
          </p>
        </div>
        <p className="text-primary-foreground/40 text-xs">© 2026 LicitaAI</p>
      </div>

      {/* Formulário */}
      <div className="flex flex-1 items-center justify-center bg-background px-6 py-12">
        <div className="w-full max-w-sm space-y-8">
          <div className="lg:hidden flex items-center gap-2.5">
            <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-bold">LA</span>
            <span className="font-bold text-lg tracking-tight text-foreground">Licita<span className="text-primary">AI</span></span>
          </div>

          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">Criar conta</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Já tem conta?{" "}
              <Link href="/login" className="text-primary font-medium hover:underline">
                Entrar
              </Link>
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-foreground" htmlFor="nome">
                Nome completo
              </label>
              <Input
                id="nome"
                type="text"
                required
                placeholder="Seu nome"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                className="h-10"
              />
            </div>
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
                minLength={6}
                placeholder="Mínimo 6 caracteres"
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
              {loading ? "Criando..." : "Criar conta"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
