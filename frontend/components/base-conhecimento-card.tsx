"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { validarEvidencia } from "@/lib/api-client";
import type {
  BaseConhecimento,
  EvidenciaBCC,
  LacunaBCC,
  RiscoBCC,
} from "@/lib/types";

interface Props {
  bcc: BaseConhecimento;
  contratacaoId: number;
  onUpdate?: (bcc: BaseConhecimento) => void;
}

// ── helpers ────────────────────────────────────────────────────────────────────

function badgeCriticidade(c: "alta" | "média" | "baixa") {
  const cls = {
    alta: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
    média: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
    baixa: "bg-muted text-muted-foreground",
  }[c];
  return <Badge className={cls}>{c}</Badge>;
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

function badgeValidacao(s: string) {
  const cls: Record<string, string> = {
    validada: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
    pendente: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
    frágil: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
    contraditória: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
  };
  return <Badge className={cls[s] ?? "bg-muted"}>{s}</Badge>;
}

function nivelRiscoOrder(n: string) {
  return { crítico: 0, alto: 1, médio: 2, baixo: 3 }[n] ?? 4;
}

// ── sub-componentes por aba ────────────────────────────────────────────────────

function AbaEvidencias({
  evidencias,
  contratacaoId,
  onUpdate,
}: {
  evidencias: EvidenciaBCC[];
  contratacaoId: number;
  onUpdate?: (bcc: BaseConhecimento) => void;
}) {
  type Filtro = "todas" | "validada" | "pendente" | "frágil" | "contraditória";
  const [filtro, setFiltro] = useState<Filtro>("todas");
  const [validando, setValidando] = useState<number | null>(null);

  const FILTROS: Filtro[] = ["todas", "validada", "pendente", "frágil", "contraditória"];
  const filtradas =
    filtro === "todas" ? evidencias : evidencias.filter((e) => e.status_validacao === filtro);

  async function handleValidar(idx: number) {
    setValidando(idx);
    try {
      const bcc = await validarEvidencia(contratacaoId, idx, "validada");
      onUpdate?.(bcc);
    } finally {
      setValidando(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2 flex-wrap">
        {FILTROS.map((f) => (
          <button
            key={f}
            onClick={() => setFiltro(f)}
            className={[
              "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
              filtro === f
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border hover:bg-muted",
            ].join(" ")}
          >
            {f === "todas" ? "Todas" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {filtradas.length === 0 && (
        <p className="text-sm text-muted-foreground">Nenhuma evidência neste filtro.</p>
      )}

      <div className="flex flex-col gap-3">
        {filtradas.map((ev, i) => {
          const idxReal = evidencias.indexOf(ev);
          return (
            <Card key={ev.id ?? i} className="text-sm">
              <CardContent className="pt-4 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{ev.descricao}</p>
                  {badgeValidacao(ev.status_validacao)}
                </div>
                <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                  <span>Origem: {ev.origem}</span>
                  <span>
                    Confiabilidade:{" "}
                    <span
                      className={
                        ev.confiabilidade === "alta"
                          ? "text-emerald-600"
                          : ev.confiabilidade === "média"
                            ? "text-amber-600"
                            : "text-muted-foreground"
                      }
                    >
                      {ev.confiabilidade}
                    </span>
                  </span>
                  <span>Responsável: {ev.responsavel}</span>
                </div>
                {ev.documentos_impactados?.length > 0 && (
                  <div className="flex gap-1 flex-wrap">
                    {ev.documentos_impactados.map((d) => (
                      <span
                        key={d}
                        className="px-1.5 py-0.5 bg-muted rounded text-xs text-muted-foreground"
                      >
                        {d}
                      </span>
                    ))}
                  </div>
                )}
                {ev.status_validacao !== "validada" && (
                  <Button
                    variant="outline"
                    size="xs"
                    disabled={validando === idxReal}
                    onClick={() => handleValidar(idxReal)}
                    className="w-fit"
                  >
                    {validando === idxReal ? "Validando…" : "Validar evidência"}
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function AbaLacunas({ lacunas }: { lacunas: LacunaBCC[] }) {
  const ordenadas = [...lacunas].sort((a, b) => {
    const ord = { alta: 0, média: 1, baixa: 2 };
    return (ord[a.criticidade] ?? 3) - (ord[b.criticidade] ?? 3);
  });

  if (ordenadas.length === 0)
    return <p className="text-sm text-muted-foreground">Nenhuma lacuna identificada.</p>;

  return (
    <div className="flex flex-col gap-3">
      {ordenadas.map((l, i) => (
        <Card key={l.id ?? i} className="text-sm">
          <CardContent className="pt-4 flex flex-col gap-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium">{l.descricao}</p>
              {badgeCriticidade(l.criticidade)}
            </div>
            <p className="text-muted-foreground text-xs">
              Ação necessária: {l.acao_necessaria}
            </p>
            {l.documentos_bloqueados?.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                <span className="text-xs text-muted-foreground">Bloqueia:</span>
                {l.documentos_bloqueados.map((d) => (
                  <span
                    key={d}
                    className="px-1.5 py-0.5 bg-red-50 dark:bg-red-950/30 text-red-600 rounded text-xs"
                  >
                    {d}
                  </span>
                ))}
              </div>
            )}
            <p className="text-xs text-muted-foreground">Responsável: {l.responsavel}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function AbaRiscos({ riscos }: { riscos: RiscoBCC[] }) {
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
            <p className="text-xs text-muted-foreground">
              Ação preventiva: {r.acao_preventiva}
            </p>
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

// ── componente principal ───────────────────────────────────────────────────────

export function BaseConhecimentoCard({ bcc: bccProp, contratacaoId, onUpdate }: Props) {
  const [bcc, setBcc] = useState(bccProp);
  const dados = bcc.dados;
  const m = dados.metricas;

  function handleUpdate(updated: BaseConhecimento) {
    setBcc(updated);
    onUpdate?.(updated);
  }

  const maturidadeColor =
    m.nivel_maturidade === "Maduro"
      ? "text-emerald-600"
      : m.nivel_maturidade === "Parcial"
        ? "text-amber-600"
        : "text-destructive";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Base de Conhecimento da Contratação</CardTitle>

        {/* Métricas resumo */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-2">
          {[
            {
              label: "Progresso",
              value: (
                <span className="font-semibold text-primary">{m.progresso_pct}%</span>
              ),
            },
            {
              label: "Maturidade",
              value: (
                <span className={`font-semibold ${maturidadeColor}`}>
                  {m.nivel_maturidade}
                </span>
              ),
            },
            {
              label: "Evidências",
              value: `${m.evidencias_coletadas} de ${m.evidencias_total}`,
            },
            {
              label: "Decisões",
              value: `${m.decisoes_fundamentadas} de ${m.decisoes_total}`,
            },
            {
              label: "Pendências críticas",
              value: (
                <span className={m.pendencias_criticas > 0 ? "text-destructive font-semibold" : ""}>
                  {m.pendencias_criticas}
                </span>
              ),
            },
            {
              label: "Atualizado em",
              value: bcc.atualizado_em
                ? new Date(bcc.atualizado_em).toLocaleString("pt-BR")
                : "—",
            },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-border p-2.5">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm mt-0.5">{value}</p>
            </div>
          ))}
        </div>

        <div className="mt-2">
          <Progress value={m.progresso_pct} />
        </div>
      </CardHeader>

      <Separator />

      <CardContent className="pt-4">
        <Tabs defaultValue="evidencias">
          <TabsList
            variant="line"
            className="w-full justify-start border-b border-border rounded-none pb-0 h-auto flex-wrap gap-y-1"
          >
            {[
              ["evidencias", "Evidências"],
              ["decisoes", "Decisões e Análises"],
              ["lacunas", "Lacunas e Pendências"],
              ["riscos", "Riscos"],
              ["recomendacoes", "Recomendações"],
              ["documentos", "Documentos"],
              ["historico", "Histórico"],
            ].map(([val, label]) => (
              <TabsTrigger key={val} value={val} className="px-3 pb-3 rounded-none text-xs sm:text-sm">
                {label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="evidencias" className="mt-4">
            <AbaEvidencias
              evidencias={dados.evidencias ?? []}
              contratacaoId={contratacaoId}
              onUpdate={handleUpdate}
            />
          </TabsContent>

          <TabsContent value="decisoes" className="mt-4">
            {(dados.decisoes ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma decisão registrada.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {dados.decisoes.map((d, i) => (
                  <Card key={d.id ?? i} className="text-sm">
                    <CardContent className="pt-4 flex flex-col gap-2">
                      <p className="font-semibold text-foreground">{d.pergunta_decisoria}</p>
                      <p className="text-primary font-medium">{d.conclusao}</p>
                      <p className="text-muted-foreground text-xs">{d.motivacao_administrativa}</p>
                      {d.base_legal && (
                        <p className="text-xs text-muted-foreground">Base legal: {d.base_legal}</p>
                      )}
                      <div className="flex items-center gap-3 mt-1">
                        <div className="flex-1">
                          <Progress value={d.nivel_robustez_pct} />
                        </div>
                        <span className="text-xs font-medium whitespace-nowrap">
                          Robustez: {d.nivel_robustez_pct}% — {d.nivel_robustez_label}
                        </span>
                      </div>
                      {(d.documentos_impactados ?? []).length > 0 && (
                        <div className="flex gap-1 flex-wrap">
                          {d.documentos_impactados.map((doc) => (
                            <span
                              key={doc}
                              className="px-1.5 py-0.5 bg-muted rounded text-xs text-muted-foreground"
                            >
                              {doc}
                            </span>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="lacunas" className="mt-4">
            <AbaLacunas lacunas={dados.lacunas ?? []} />
          </TabsContent>

          <TabsContent value="riscos" className="mt-4">
            <AbaRiscos riscos={dados.riscos ?? []} />
          </TabsContent>

          <TabsContent value="recomendacoes" className="mt-4">
            {(dados.recomendacoes ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhuma recomendação.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {dados.recomendacoes.map((r, i) => (
                  <Card key={r.id ?? i} className="text-sm">
                    <CardContent className="pt-4 flex flex-col gap-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-medium">{r.descricao}</p>
                        {badgeCriticidade(r.prioridade)}
                      </div>
                      <p className="text-xs text-muted-foreground">Motivo: {r.motivo}</p>
                      <p className="text-xs text-muted-foreground">
                        Benefício: {r.beneficio_esperado}
                      </p>
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
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="documentos" className="mt-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead>Situação</TableHead>
                  <TableHead>Completude</TableHead>
                  <TableHead>Pendências</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(dados.documentos_status ?? {}).map(([doc, info]) => (
                  <TableRow key={doc}>
                    <TableCell className="font-medium">{doc}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{info.situacao}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-24">
                          <Progress value={info.completude_pct} />
                        </div>
                        <span className="text-xs text-muted-foreground">{info.completude_pct}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          info.pendencias > 0 ? "text-destructive font-medium" : "text-muted-foreground"
                        }
                      >
                        {info.pendencias}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>

          <TabsContent value="historico" className="mt-4">
            {(dados.historico ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum registro.</p>
            ) : (
              <div className="flex flex-col gap-2">
                {[...dados.historico].reverse().map((h, i) => (
                  <div key={i} className="text-sm border-l-2 border-muted pl-3 py-1">
                    <p className="text-muted-foreground text-xs">
                      {new Date(h.timestamp).toLocaleString("pt-BR")} — {h.usuario}
                    </p>
                    <p className="font-medium">{h.acao}</p>
                    {h.detalhe && <p className="text-xs text-muted-foreground">{h.detalhe}</p>}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
