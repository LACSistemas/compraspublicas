"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Button } from "@/components/ui/button";
import { Search, FileText, Bot, ClipboardList } from "lucide-react";
import Link from "next/link";

const features = [
  { icon: Search, label: "Scraping automático", desc: "Coleta dados de portais de licitação" },
  { icon: Bot, label: "Análise com IA", desc: "Identifica inconsistências e riscos" },
  { icon: FileText, label: "Geração ETP & TR", desc: "Documentos gerados com base na legislação" },
  { icon: ClipboardList, label: "Assistente de Planejamento", desc: "Constrói a base de conhecimento antes de gerar documentos" },
];

export default function Home() {
  return (
    <AuthGuard>
      <main className="flex flex-1 flex-col items-center justify-center px-6 py-16 bg-background">
        <div className="w-full max-w-2xl text-center space-y-8">
          {/* Logo */}
          <div className="flex justify-center">
            <div className="flex items-center gap-3">
              <span className="flex items-center justify-center w-12 h-12 rounded-xl bg-primary text-primary-foreground text-base font-bold tracking-tight select-none shadow-sm">
                LA
              </span>
              <span className="font-extrabold text-3xl tracking-tight text-foreground">
                Licita<span className="text-primary">AI</span>
              </span>
            </div>
          </div>

          {/* Headline */}
          <div className="space-y-3">
            <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-foreground leading-tight">
              Auditoria inteligente de{" "}
              <span className="text-primary">compras públicas</span>
            </h1>
            <p className="text-base text-muted-foreground max-w-lg mx-auto leading-relaxed">
              Pesquise processos licitatórios, analise documentos com IA e gere ETP e TR em conformidade com a Lei 14.133/2021.
            </p>
          </div>

          {/* Feature pills */}
          <div className="flex flex-wrap justify-center gap-3">
            {features.map(({ icon: Icon, label, desc }) => (
              <div
                key={label}
                className="flex items-center gap-2.5 rounded-xl border border-border bg-card px-4 py-3 text-left shadow-xs"
              >
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10">
                  <Icon className="size-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">{label}</p>
                  <p className="text-xs text-muted-foreground">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 flex-wrap">
            <Button size="lg" className="h-11 px-8 font-semibold text-sm" render={<Link href="/contratacoes/nova" />}>
              Nova Contratação
            </Button>
            <Button size="lg" variant="outline" className="h-11 px-8 font-semibold text-sm" render={<Link href="/nova-pesquisa" />}>
              Nova Pesquisa
            </Button>
            <Button size="lg" variant="ghost" className="h-11 px-8 font-semibold text-sm" render={<Link href="/pesquisas" />}>
              Ver Pesquisas
            </Button>
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}
