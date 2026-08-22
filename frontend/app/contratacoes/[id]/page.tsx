"use client";

import { use, useState } from "react";
import Link from "next/link";
import { AuthGuard } from "@/components/auth-guard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { InvestigacaoFlow } from "@/components/investigacao-flow";
import { BaseConhecimentoCard } from "@/components/base-conhecimento-card";
import { AnaliseIaCard } from "@/components/analise-ia-card";
import { usePolling } from "@/lib/use-pesquisa-polling";
import { getContratacao, getEstatisticasTokens, iniciarInvestigacao } from "@/lib/api-client";
import type { Contratacao, StatusContratacao, TokensPorContratacao } from "@/lib/types";

// ── StepIndicator ─────────────────────────────────────────────────────────────

const STEPS = ["Cadastro", "Investigação", "Processando", "Base Pronta", "Documentos"];

function stepFromStatus(status: StatusContratacao): number {
  if (status === "cadastro") return 1;
  if (status === "gerando_perguntas" || status === "investigacao") return 2;
  if (status === "processando_bcc") return 3;
  if (status === "bcc_ativa") return 4;
  return 1;
}

function StepIndicator({ status }: { status: StatusContratacao }) {
  const current = stepFromStatus(status);
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {STEPS.map((label, i) => {
        const step = i + 1;
        const done = step < current;
        const active = step === current;
        const disabled = step === 5;
        return (
          <div key={label} className="flex items-center gap-1">
            <div
              className={[
                "h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors",
                done
                  ? "bg-emerald-500 text-white"
                  : active
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                disabled ? "opacity-40" : "",
              ].join(" ")}
            >
              {done ? "✓" : step}
            </div>
            <span
              className={[
                "text-xs hidden sm:inline",
                active ? "font-semibold text-foreground" : "text-muted-foreground",
                disabled ? "opacity-40" : "",
              ].join(" ")}
            >
              {label}
            </span>
            {i < STEPS.length - 1 && (
              <div
                className={[
                  "h-px w-4 hidden sm:block mx-1",
                  done ? "bg-emerald-400" : "bg-border",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Status body ───────────────────────────────────────────────────────────────

function LoadingBlock({ texto }: { texto: string }) {
  return (
    <Card>
      <CardContent className="pt-6 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-sm text-muted-foreground">{texto}</p>
        </div>
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </CardContent>
    </Card>
  );
}

function fmt(n: number) {
  return n.toLocaleString("pt-BR");
}

function BccAtivaBody({ contratacao }: { contratacao: Contratacao }) {
  const [tokenInfo, setTokenInfo] = useState<TokensPorContratacao | null>(null);
  const [aberto, setAberto] = useState(false);

  // Busca única após BCC estar ativa
  useState(() => {
    getEstatisticasTokens()
      .then((est) => {
        const info = est.por_contratacao.find((p) => p.contratacao_id === contratacao.id);
        if (info) setTokenInfo(info);
      })
      .catch(() => null);
  });

  return (
    <div className="flex flex-col gap-6">
      <BaseConhecimentoCard
        bcc={contratacao.base_conhecimento!}
        contratacaoId={contratacao.id}
      />
      <AnaliseIaCard dados={contratacao.base_conhecimento!.dados} />

      {/* Consumo de tokens desta contratação */}
      {tokenInfo && (tokenInfo.tokens_perguntas_total > 0 || tokenInfo.tokens_bcc_total > 0) && (
        <div className="rounded-lg border border-border">
          <button
            onClick={() => setAberto((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <span>Consumo de tokens nesta contratação</span>
            <span className="text-xs">{aberto ? "▲ Recolher" : "▼ Expandir"}</span>
          </button>
          {aberto && (
            <div className="px-4 pb-4 border-t border-border mt-0 pt-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                {[
                  {
                    label: "Fase — Perguntas",
                    input: tokenInfo.tokens_perguntas_input,
                    output: tokenInfo.tokens_perguntas_output,
                    total: tokenInfo.tokens_perguntas_total,
                  },
                  {
                    label: "Fase — Base de Conhecimento",
                    input: tokenInfo.tokens_bcc_input,
                    output: tokenInfo.tokens_bcc_output,
                    total: tokenInfo.tokens_bcc_total,
                  },
                  {
                    label: "Total",
                    input: tokenInfo.tokens_perguntas_input + tokenInfo.tokens_bcc_input,
                    output: tokenInfo.tokens_perguntas_output + tokenInfo.tokens_bcc_output,
                    total: tokenInfo.total,
                  },
                ].map(({ label, input, output, total }) => (
                  <div key={label} className="rounded-md border border-border p-3 flex flex-col gap-1">
                    <p className="text-xs font-semibold text-muted-foreground">{label}</p>
                    <div className="flex flex-col gap-0.5 text-xs text-muted-foreground">
                      <span>Input: <span className="text-foreground font-medium tabular-nums">{fmt(input)}</span></span>
                      <span>Output: <span className="text-foreground font-medium tabular-nums">{fmt(output)}</span></span>
                      <span>Total: <span className="text-primary font-semibold tabular-nums">{fmt(total)}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBody({
  contratacao,
  onAtualizar,
}: {
  contratacao: Contratacao;
  onAtualizar: () => void;
}) {
  const [iniciando, setIniciando] = useState(false);
  const [erroIniciar, setErroIniciar] = useState<string | null>(null);

  async function handleIniciarInvestigacao() {
    setErroIniciar(null);
    setIniciando(true);
    try {
      await iniciarInvestigacao(contratacao.id);
      onAtualizar();
    } catch (e) {
      setErroIniciar(e instanceof Error ? e.message : "Erro ao iniciar investigação");
    } finally {
      setIniciando(false);
    }
  }

  const { status } = contratacao;

  if (status === "cadastro") {
    return (
      <Card>
        <CardContent className="pt-6 flex flex-col gap-4">
          <div>
            <p className="font-semibold">Contratação registrada</p>
            <p className="text-sm text-muted-foreground mt-1">
              Clique em "Iniciar Investigação" para a IA gerar 25 perguntas específicas sobre este
              processo. As respostas serão usadas para construir a Base de Conhecimento.
            </p>
          </div>
          {erroIniciar && (
            <Alert variant="destructive">
              <AlertDescription>{erroIniciar}</AlertDescription>
            </Alert>
          )}
          <Button
            onClick={handleIniciarInvestigacao}
            disabled={iniciando}
            size="lg"
            className="w-fit"
          >
            {iniciando ? "Iniciando…" : "Iniciar Investigação"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (status === "gerando_perguntas") {
    return <LoadingBlock texto="A IA está gerando as perguntas de investigação…" />;
  }

  if (status === "investigacao") {
    return (
      <InvestigacaoFlow
        perguntas={contratacao.perguntas}
        contratacaoId={contratacao.id}
        onProcessarIniciado={onAtualizar}
      />
    );
  }

  if (status === "processando_bcc") {
    return <LoadingBlock texto="Construindo a Base de Conhecimento da Contratação…" />;
  }

  if (status === "bcc_ativa" && contratacao.base_conhecimento) {
    return (
      <BccAtivaBody
        contratacao={contratacao}
      />
    );
  }

  if (status === "erro") {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          <p className="font-medium mb-1">Erro no processamento</p>
          <p className="text-sm">{contratacao.erro_mensagem || "Erro desconhecido."}</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={handleIniciarInvestigacao}
            disabled={iniciando}
          >
            Tentar novamente
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}

// ── Página principal ──────────────────────────────────────────────────────────

function ContratacaoDetalhePage({ id }: { id: number }) {
  const TERMINAL: StatusContratacao[] = ["bcc_ativa", "erro"];

  const { data: contratacao, erro } = usePolling<Contratacao>({
    fetchFn: () => getContratacao(id),
    intervalMs: 3000,
    shouldStop: (c) => TERMINAL.includes(c.status),
  });

  if (erro) {
    return (
      <div className="flex flex-1 flex-col p-8">
        <Alert variant="destructive">
          <AlertDescription>{erro.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!contratacao) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-8">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-8 max-w-4xl mx-auto w-full">
      {/* Cabeçalho */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link href="/contratacoes" className="hover:text-foreground transition-colors">
            Contratações
          </Link>
          <span>/</span>
          <span className="truncate max-w-xs">{contratacao.objeto}</span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold leading-snug">{contratacao.objeto}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap text-sm text-muted-foreground">
              <span>{contratacao.orgao_unidade}</span>
              {contratacao.numero_processo && (
                <>
                  <span>·</span>
                  <span>{contratacao.numero_processo}</span>
                </>
              )}
              {contratacao.tipo_contratacao && (
                <>
                  <span>·</span>
                  <Badge variant="secondary" className="text-xs">
                    {contratacao.tipo_contratacao}
                  </Badge>
                </>
              )}
            </div>
          </div>
          <StepIndicator status={contratacao.status} />
        </div>
      </div>

      {/* Corpo de status */}
      <StatusBody
        contratacao={contratacao}
        onAtualizar={() => {
          // O polling vai pegar a atualização no próximo tick automaticamente
        }}
      />
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <AuthGuard>
      <ContratacaoDetalhePage id={Number(id)} />
    </AuthGuard>
  );
}
