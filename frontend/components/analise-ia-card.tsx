"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { DadosBCC, RiscoBCC } from "@/lib/types";
import { revisarRecomendacao } from "@/lib/api-client";

interface Props {
  dados: DadosBCC;
  contratacaoId: number;
}

function badgePrioridade(p: "alta" | "média" | "baixa") {
  const cls = {
    alta: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
    média: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
    baixa: "bg-muted text-muted-foreground",
  }[p];
  return <Badge className={cls}>{p}</Badge>;
}

function badgeNivelRisco(n: string) {
  const cls: Record<string, string> = {
    crítico: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
    alto: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
    médio: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
    baixo: "bg-muted text-muted-foreground",
  };
  return <Badge className={cls[n] ?? ""}>{n}</Badge>;
}

function nivelRiscoOrder(n: string) {
  return { crítico: 0, alto: 1, médio: 2, baixo: 3 }[n] ?? 4;
}

function AbaRiscosDetalhado({ riscos }: { riscos: RiscoBCC[] }) {
  const ordenados = [...riscos].sort(
    (a, b) => nivelRiscoOrder(a.nivel_risco) - nivelRiscoOrder(b.nivel_risco),
  );

  if (ordenados.length === 0)
    return <p className="text-sm text-muted-foreground">Nenhum risco identificado.</p>;

  return (
    <div className="flex flex-col gap-3">
      {ordenados.map((r, i) => (
        <Card key={r.id ?? i} className="text-sm">
          <CardContent className="pt-4 flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium">{r.descricao}</p>
              {badgeNivelRisco(r.nivel_risco)}
            </div>
            <div className="flex gap-4 text-xs text-muted-foreground">
              <span>Probabilidade: {r.probabilidade}</span>
              <span>Impacto: {r.impacto}</span>
              <span>Categoria: {r.categoria}</span>
            </div>
            {r.causa && (
              <p className="text-xs text-muted-foreground">Causa: {r.causa}</p>
            )}
            {r.consequencia && (
              <p className="text-xs text-muted-foreground">Consequência: {r.consequencia}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Ação preventiva: {r.acao_preventiva}
            </p>
            {r.plano_contingencia && (
              <p className="text-xs text-muted-foreground">
                Plano de contingência: {r.plano_contingencia}
              </p>
            )}
            {r.responsavel && (
              <p className="text-xs text-muted-foreground">Responsável: {r.responsavel}</p>
            )}
            {r.fonte === "ia" && (
              <span className="text-xs px-1.5 py-0.5 bg-muted rounded w-fit text-muted-foreground">
                Gerado pela IA
              </span>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function AnaliseIaCard({ dados, contratacaoId }: Props) {
  const fundamentacoes = dados.fundamentacoes ?? [];
  const robustezMedia =
    fundamentacoes.length > 0
      ? Math.round(
          fundamentacoes.reduce((s, f) => s + (f.nivel_robustez_pct ?? 0), 0) /
            fundamentacoes.length,
        )
      : 0;

  const [expandidos, setExpandidos] = useState<Set<number>>(new Set());
  const [statusRecomendacoes, setStatusRecomendacoes] = useState<Record<number, string>>(
    () => Object.fromEntries((dados.recomendacoes ?? []).map((item, idx) => [idx, item.status ?? "pendente"])),
  );
  const [recomendacaoEmAndamento, setRecomendacaoEmAndamento] = useState<number | null>(null);
  const [erroRecomendacao, setErroRecomendacao] = useState<string | null>(null);

  async function decidirRecomendacao(idx: number, decisao: "executar" | "dispensar") {
    setRecomendacaoEmAndamento(idx);
    setErroRecomendacao(null);
    try {
      await revisarRecomendacao(contratacaoId, idx, decisao);
      setStatusRecomendacoes((atual) => ({
        ...atual,
        [idx]: decisao === "executar" ? "executada" : "dispensada",
      }));
    } catch (error) {
      setErroRecomendacao(error instanceof Error ? error.message : "Falha ao registrar a decisão");
    } finally {
      setRecomendacaoEmAndamento(null);
    }
  }
  function toggleExpandido(i: number) {
    setExpandidos((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Análises e Justificativas Geradas pela IA</CardTitle>
        <div className="flex flex-wrap gap-3 mt-1">
          {[
            {
              label: "Evidências analisadas",
              value: dados.metricas?.evidencias_coletadas ?? 0,
            },
            {
              label: "Decisões fundamentadas",
              value: dados.metricas?.decisoes_fundamentadas ?? 0,
            },
            {
              label: "Robustez média",
              value: (
                <span className="flex items-center gap-2">
                  <div className="w-16">
                    <Progress value={robustezMedia} />
                  </div>
                  <span>{robustezMedia}%</span>
                </span>
              ),
            },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-border px-3 py-2">
              <p className="text-xs text-muted-foreground">{label}</p>
              <div className="text-sm font-medium mt-0.5">{value}</div>
            </div>
          ))}
        </div>
      </CardHeader>

      <Separator />

      <CardContent className="pt-4">
        <Tabs defaultValue="resumo">
          <TabsList
            variant="line"
            className="w-full justify-start border-b border-border rounded-none pb-0 h-auto"
          >
            {[
              ["resumo", "Resumo Executivo"],
              ["fundamentacoes", "Fundamentações"],
              ["riscos", "Riscos"],
              ["recomendacoes", "Recomendações"],
            ].map(([val, label]) => (
              <TabsTrigger
                key={val}
                value={val}
                className="px-3 pb-3 rounded-none text-xs sm:text-sm"
              >
                {label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="resumo" className="mt-4">
            <div className="flex flex-col gap-4">
              <div className="rounded-lg border border-border p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Necessidade
                </p>
                <p className="text-sm">{dados.resumo_executivo?.necessidade || "—"}</p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Solução Escolhida e Vantajosidade
                </p>
                <p className="text-sm">{dados.resumo_executivo?.solucao_escolhida || "—"}</p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Riscos Principais
                </p>
                {(dados.resumo_executivo?.riscos_principais ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nenhum risco identificado.</p>
                ) : (
                  <ul className="list-disc list-inside flex flex-col gap-1">
                    {dados.resumo_executivo.riscos_principais.map((r, i) => (
                      <li key={i} className="text-sm">
                        {r}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="fundamentacoes" className="mt-4">
            {fundamentacoes.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma fundamentação.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {fundamentacoes.map((f, i) => {
                  const aberta = expandidos.has(i);
                  return (
                    <Card key={f.id ?? i} className="text-sm">
                      <CardContent className="pt-4 flex flex-col gap-2">
                        <p className="font-semibold text-foreground">{f.pergunta_decisoria}</p>
                        <p className="text-primary font-medium">{f.conclusao}</p>

                        {/* Justificativa expandível */}
                        <div>
                          <p className={aberta ? "" : "line-clamp-3"}>
                            {f.justificativa_administrativa}
                          </p>
                          {f.justificativa_administrativa?.length > 200 && (
                            <button
                              onClick={() => toggleExpandido(i)}
                              className="text-xs text-primary mt-1 hover:underline"
                            >
                              {aberta ? "Ver menos" : "Ver mais"}
                            </button>
                          )}
                        </div>

                        {(f.evidencias_utilizadas ?? []).length > 0 && (
                          <div className="flex gap-1 flex-wrap">
                            <span className="text-xs text-muted-foreground">Evidências:</span>
                            {f.evidencias_utilizadas.map((ev) => (
                              <span
                                key={ev}
                                className="px-1.5 py-0.5 bg-muted rounded text-xs text-muted-foreground"
                              >
                                {ev}
                              </span>
                            ))}
                          </div>
                        )}

                        {(f.base_normativa ?? []).length > 0 && (
                          <ul className="list-disc list-inside flex flex-col gap-0.5">
                            {f.base_normativa.map((b) => (
                              <li key={b} className="text-xs text-muted-foreground">
                                {b}
                              </li>
                            ))}
                          </ul>
                        )}

                        <div className="flex items-center gap-3 mt-1">
                          <div className="flex-1">
                            <Progress value={f.nivel_robustez_pct} />
                          </div>
                          <span className="text-xs font-medium whitespace-nowrap">
                            Robustez: {f.nivel_robustez_pct}% — {f.nivel_robustez_label}
                          </span>
                        </div>

                        {f.ressalvas && (
                          <div className="rounded-md bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 p-3 text-xs text-amber-800 dark:text-amber-300">
                            <span className="font-semibold">Ressalvas: </span>
                            {f.ressalvas}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          <TabsContent value="riscos" className="mt-4">
            <AbaRiscosDetalhado riscos={dados.riscos ?? []} />
          </TabsContent>

          <TabsContent value="recomendacoes" className="mt-4">
            {erroRecomendacao && <p className="mb-3 text-sm text-destructive">{erroRecomendacao}</p>}
            {(dados.recomendacoes ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma recomendação.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {dados.recomendacoes.map((r, i) => (
                  <Card key={r.id ?? i} className="text-sm">
                    <CardContent className="pt-4 flex flex-col gap-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Ação proposta</p>
                          <p className="font-medium mt-1">{r.descricao}</p>
                        </div>
                        {badgePrioridade(r.prioridade)}
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2 mt-1">
                        <div className="rounded-md bg-muted/50 p-3">
                          <p className="text-xs font-semibold">Por que isso importa</p>
                          <p className="text-xs text-muted-foreground mt-1">{r.motivo}</p>
                        </div>
                        <div className="rounded-md bg-muted/50 p-3">
                          <p className="text-xs font-semibold">Resultado esperado</p>
                          <p className="text-xs text-muted-foreground mt-1">{r.beneficio_esperado}</p>
                        </div>
                      </div>
                      {r.risco_reduzido && (
                        <p className="text-xs text-muted-foreground">
                          Risco reduzido: {r.risco_reduzido}
                        </p>
                      )}
                      {(r.documentos_impactados ?? []).length > 0 && (
                        <div className="flex gap-1 flex-wrap">
                          {r.documentos_impactados.map((d) => (
                            <span
                              key={d}
                              className="px-1.5 py-0.5 bg-muted rounded text-xs text-muted-foreground"
                            >
                              {d}
                            </span>
                          ))}
                        </div>
                      )}
                      {statusRecomendacoes[i] === "pendente" ? (
                        <div className="flex gap-2 mt-1">
                          <button type="button" disabled={recomendacaoEmAndamento !== null}
                            onClick={() => void decidirRecomendacao(i, "executar")}
                            className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium disabled:opacity-50">
                            {recomendacaoEmAndamento === i ? "Salvando…" : "Incorporar aos documentos"}
                          </button>
                          <button type="button" disabled={recomendacaoEmAndamento !== null}
                            onClick={() => void decidirRecomendacao(i, "dispensar")}
                            className="text-xs px-3 py-1.5 rounded-md border border-border hover:bg-muted transition-colors disabled:opacity-50">
                            Não incorporar
                          </button>
                        </div>
                      ) : (
                        <Badge variant="outline" className="w-fit mt-1">
                          {statusRecomendacoes[i] === "executada" ? "Execução aprovada" : "Dispensada"}
                        </Badge>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
