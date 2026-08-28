"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AuthGuard } from "@/components/auth-guard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getEstatisticasTokens, listarContratacoes } from "@/lib/api-client";
import { TokenStatsCard } from "@/components/token-stats-card";
import type { Contratacao, EstatisticasTokensOut, StatusContratacao } from "@/lib/types";

export default function ContratacaoesPage() {
  return (
    <AuthGuard>
      <ContratacaoesContent />
    </AuthGuard>
  );
}

const LABEL_STATUS: Record<StatusContratacao, string> = {
  cadastro: "Cadastro",
  gerando_plano: "Gerando plano…",
  gerando_perguntas: "Gerando perguntas…",
  investigacao: "Em investigação",
  processando_bcc: "Processando BCC…",
  bcc_ativa: "Base pronta",
  erro: "Erro",
};

function BadgeStatus({ status }: { status: StatusContratacao }) {
  if (status === "bcc_ativa") {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
        {LABEL_STATUS[status]}
      </Badge>
    );
  }
  if (status === "gerando_plano" || status === "gerando_perguntas" || status === "processando_bcc") {
    return (
      <Badge variant="outline" className="text-amber-600 border-amber-300">
        {LABEL_STATUS[status]}
      </Badge>
    );
  }
  const variante: Record<string, "secondary" | "default" | "destructive"> = {
    cadastro: "secondary",
    investigacao: "default",
    erro: "destructive",
  };
  return (
    <Badge variant={variante[status] ?? "secondary"}>
      {LABEL_STATUS[status]}
    </Badge>
  );
}

function ContratacaoesContent() {
  const [contratacoes, setContratacoes] = useState<Contratacao[]>([]);
  const [stats, setStats] = useState<EstatisticasTokensOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listarContratacoes(), getEstatisticasTokens()])
      .then(([lista, est]) => { setContratacoes(lista); setStats(est); })
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Contratações</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Processos em fase preparatória
          </p>
        </div>
        <Button nativeButton={false} render={<Link href="/contratacoes/nova">Nova Contratação</Link>} />
      </div>

      {/* Estatísticas de tokens do usuário */}
      {stats && stats.perguntas.total_chamadas > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Consumo de tokens nas suas contratações
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <TokenStatsCard titulo="Geração de Perguntas" stats={stats.perguntas} compact />
            <TokenStatsCard titulo="Base de Conhecimento" stats={stats.bcc} compact />
          </div>
        </div>
      )}

      {loading && <p className="text-sm text-muted-foreground">Carregando…</p>}
      {erro && <p className="text-sm text-destructive">{erro}</p>}

      {!loading && !erro && contratacoes.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhuma contratação ainda.{" "}
          <Link href="/contratacoes/nova" className="text-primary hover:underline">
            Criar a primeira
          </Link>
        </p>
      )}

      {!loading && !erro && contratacoes.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Objeto</TableHead>
              <TableHead>Órgão</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Data</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {contratacoes.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium max-w-xs truncate">{c.objeto}</TableCell>
                <TableCell className="text-muted-foreground">{c.orgao_unidade}</TableCell>
                <TableCell className="text-muted-foreground">{c.tipo_contratacao ?? "—"}</TableCell>
                <TableCell>
                  <BadgeStatus status={c.status} />
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(c.criado_em).toLocaleDateString("pt-BR")}
                </TableCell>
                <TableCell>
                  <Link
                    href={`/contratacoes/${c.id}`}
                    className="text-primary underline-offset-4 hover:underline"
                  >
                    Abrir
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
