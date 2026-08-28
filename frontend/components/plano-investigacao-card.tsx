"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { coletarPlano, consolidarBccPlano, gerarConhecimentosPlano, getConhecimentosPlano, getEvidenciasPlano, getLacunasPlano, getPlanoInvestigacao, revisarConhecimentoPlano, revisarDispensaCard, validarEvidenciaPlano, vincularCriteriosEvidencia } from "@/lib/api-client";
import type { ConhecimentoCard, EvidenciaPlano, PlanoInvestigacao, ResumoLacunasPlano } from "@/lib/types";

export function PlanoInvestigacaoCard({ contratacaoId }: { contratacaoId: number }) {
  const [plano, setPlano] = useState<PlanoInvestigacao | null>(null);
  const [evidencias, setEvidencias] = useState<EvidenciaPlano[]>([]);
  const [conhecimentos, setConhecimentos] = useState<ConhecimentoCard[]>([]);
  const [lacunas, setLacunas] = useState<ResumoLacunasPlano | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [acao, setAcao] = useState<string | null>(null);
  const [criteriosEdicao, setCriteriosEdicao] = useState<Record<number, string[]>>({});
  const [detalhesAbertos, setDetalhesAbertos] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [p, e, c, l] = await Promise.all([
        getPlanoInvestigacao(contratacaoId),
        getEvidenciasPlano(contratacaoId),
        getConhecimentosPlano(contratacaoId),
        getLacunasPlano(contratacaoId),
      ]);
      setPlano(p);
      setEvidencias(e);
      setConhecimentos(c);
      setLacunas(l);
      setErro(null);
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Falha ao carregar o Plano");
    }
  }, [contratacaoId]);

  useEffect(() => {
    const timeout = window.setTimeout(() => void carregar(), 0);
    return () => window.clearTimeout(timeout);
  }, [carregar]);

  async function executar(nome: string, fn: () => Promise<unknown>) {
    setAcao(nome);
    setErro(null);
    try {
      await fn();
      await carregar();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Falha na operação");
    } finally {
      setAcao(null);
    }
  }

  if (!plano) {
    return erro ? null : <Card><CardContent className="py-6 text-sm text-muted-foreground">Carregando Plano de Investigação…</CardContent></Card>;
  }

  const conhecimentosAtuais = Array.from(
    conhecimentos.reduce((mapa, conhecimento) => {
      const atual = mapa.get(conhecimento.plano_card_id);
      if (!atual || conhecimento.versao > atual.versao) mapa.set(conhecimento.plano_card_id, conhecimento);
      return mapa;
    }, new Map<number, ConhecimentoCard>()).values(),
  );
  const cardPorInformacao = new Map<number, number>();
  for (const card of plano.cards) {
    for (const info of card.informacoes) {
      if (info.id !== null) cardPorInformacao.set(info.id, card.id);
    }
  }

  function criteriosDaEvidencia(evidencia: EvidenciaPlano) {
    const planoCardId = cardPorInformacao.get(evidencia.plano_informacao_id);
    return conhecimentosAtuais.find((item) => item.plano_card_id === planoCardId)
      ?.cobertura_criterios ?? [];
  }

  function alternarCriterio(evidencia: EvidenciaPlano, codigo: string) {
    setCriteriosEdicao((atual) => {
      const selecionados = atual[evidencia.id] ?? evidencia.criterios_atendidos;
      return { ...atual, [evidencia.id]: selecionados.includes(codigo)
        ? selecionados.filter((item) => item !== codigo)
        : [...selecionados, codigo] };
    });
  }

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Detalhes técnicos da investigação</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              A IA está controlando {plano.cards.length} áreas de decisão e {lacunas?.total ?? 0} informações pendentes nos bastidores.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setDetalhesAbertos((valor) => !valor)}>
            {detalhesAbertos ? "Ocultar detalhes" : "Ver detalhes do plano"}
          </Button>
        </div>
        {erro && <Alert variant="destructive"><AlertDescription>{erro}</AlertDescription></Alert>}
      </CardHeader>
      {!detalhesAbertos && (
        <CardContent className="pt-0 text-sm text-muted-foreground">
          Você não precisa operar os Cards agora. Responda primeiro às perguntas acima; o sistema verificará as pendências automaticamente.
        </CardContent>
      )}
      {detalhesAbertos && (
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2 rounded-lg border border-border bg-muted/30 p-3">
          <Button variant="outline" size="sm" disabled={acao !== null}
            onClick={() => executar("coleta", () => coletarPlano(contratacaoId))}>
            {acao === "coleta" ? "Coletando…" : "Executar coleta automática"}
          </Button>
          <Button variant="outline" size="sm" disabled={acao !== null}
            onClick={() => executar("cards", () => gerarConhecimentosPlano(contratacaoId))}>
            {acao === "cards" ? "Avaliando…" : "Reavaliar controles"}
          </Button>
          <Button size="sm" disabled={acao !== null}
            onClick={() => executar("bcc", () => consolidarBccPlano(contratacaoId))}>
            {acao === "bcc" ? "Consolidando…" : "Consolidar tecnicamente"}
          </Button>
        </div>
        {lacunas && (
          <div className="rounded-lg border border-border p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="font-semibold">Lacunas priorizadas</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  {lacunas.bloqueantes} bloqueantes · {lacunas.opcionais} opcionais
                  {lacunas.proxima_estrategia ? ` · próxima estratégia: ${lacunas.proxima_estrategia}` : ""}
                </p>
              </div>
              <Badge variant={lacunas.pronto_para_conhecimento ? "secondary" : "outline"}>
                {lacunas.pronto_para_conhecimento ? "Pronto para avaliar" : "Coleta necessária"}
              </Badge>
            </div>
            {lacunas.lacunas.slice(0, 6).map((lacuna) => (
              <div key={lacuna.plano_informacao_id} className="flex items-center justify-between gap-3 text-sm">
                <span>{lacuna.codigo_card} · {lacuna.codigo_informacao} · {lacuna.nome_informacao}</span>
                <div className="flex gap-1">
                  <Badge variant="outline">{lacuna.estrategia}</Badge>
                  <Badge variant={lacuna.obrigatoria ? "default" : "secondary"}>
                    {lacuna.obrigatoria ? "obrigatória" : "opcional"}
                  </Badge>
                </div>
              </div>
            ))}
            {lacunas.total > 6 && <p className="text-xs text-muted-foreground">Mais {lacunas.total - 6} lacunas no Plano.</p>}
          </div>
        )}
        {plano.cards.map((card) => (
          <div key={card.id} className="rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2"><Badge variant="secondary">{card.codigo}</Badge><p className="font-semibold">{card.nome}</p></div>
                <p className="text-sm text-muted-foreground mt-1">{card.pergunta_controle}</p>
                {card.dependencias.length > 0 && <p className="text-xs text-muted-foreground mt-1">Depende de: {card.dependencias.join(", ")}</p>}
                {card.dispensa_status === "proposta" && (
                  <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
                    <p className="text-xs font-semibold">Dispensa proposta — requer decisão humana</p>
                    <p className="text-xs mt-1">{card.justificativa_dispensa}</p>
                    <div className="flex gap-2 mt-2">
                      <Button size="sm" variant="outline" disabled={acao !== null}
                        onClick={() => executar(`dispensa-${card.id}`, () => revisarDispensaCard(contratacaoId, card.id, "rejeitar"))}>Manter Card</Button>
                      <Button size="sm" disabled={acao !== null}
                        onClick={() => executar(`dispensa-${card.id}`, () => revisarDispensaCard(contratacaoId, card.id, "aprovar"))}>Aprovar dispensa</Button>
                    </div>
                  </div>
                )}
              </div>
              <span className="text-sm font-semibold tabular-nums">{card.robustez_pct}%</span>
            </div>
            <Progress value={card.robustez_pct} />
            <div className="grid gap-2 sm:grid-cols-2">
              {card.informacoes.map((info) => (
                <div key={info.codigo} className="rounded-md bg-muted/50 p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{info.codigo} · {info.nome}</span>
                    <Badge variant="outline">{info.estrategia}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{info.estado_semantico.replaceAll("_", " ")} · {info.status}{info.origem ? ` · ${info.origem}` : ""}{info.confianca ? ` · confiança ${info.confianca}` : ""}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
        {evidencias.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-semibold">Evidências normalizadas</h3>
            {evidencias.map((evidencia) => (
              <div key={evidencia.id} className="rounded-md border border-border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">#{evidencia.id} · {evidencia.descricao}</span>
                  <div className="flex gap-1"><Badge variant="outline">{evidencia.estado}</Badge><Badge variant="secondary">{evidencia.status_validacao}</Badge></div>
                </div>
                <p className="text-xs text-muted-foreground mt-1">{evidencia.origem} · {evidencia.metodo_obtencao} · confiança {evidencia.confianca}</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  <Button size="sm" variant="outline" disabled={acao !== null}
                    onClick={() => executar(`evidencia-${evidencia.id}`, () => validarEvidenciaPlano(contratacaoId, evidencia.id, "confirmada"))}>Confirmar</Button>
                  <Button size="sm" variant="outline" disabled={acao !== null}
                    onClick={() => executar(`evidencia-${evidencia.id}`, () => validarEvidenciaPlano(contratacaoId, evidencia.id, "rejeitada"))}>Rejeitar</Button>
                </div>
                {criteriosDaEvidencia(evidencia).length > 0 && (
                  <div className="mt-3 space-y-2">
                    <p className="text-xs font-medium">Critérios sustentados por esta evidência</p>
                    <div className="grid gap-1 sm:grid-cols-2">
                      {criteriosDaEvidencia(evidencia).map((criterio) => {
                        const selecionados = criteriosEdicao[evidencia.id] ?? evidencia.criterios_atendidos;
                        return <label key={criterio.codigo} className="flex gap-2 text-xs cursor-pointer">
                          <input type="checkbox" checked={selecionados.includes(criterio.codigo)}
                            onChange={() => alternarCriterio(evidencia, criterio.codigo)} />
                          <span>{criterio.codigo} · {criterio.descricao}</span>
                        </label>;
                      })}
                    </div>
                    <Button size="sm" variant="outline" disabled={acao !== null || criteriosEdicao[evidencia.id] === undefined}
                      onClick={() => executar(`criterios-${evidencia.id}`, () => vincularCriteriosEvidencia(
                        contratacaoId, evidencia.id, criteriosEdicao[evidencia.id] ?? evidencia.criterios_atendidos,
                      ))}>Salvar critérios</Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {conhecimentos.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-semibold">Conhecimento por Card</h3>
            {conhecimentosAtuais.map((conhecimento) => (
              <div key={conhecimento.id} className="rounded-md border border-border p-3 text-sm space-y-2">
                <div className="flex items-center justify-between gap-2"><span className="font-semibold">{conhecimento.codigo_card} · versão {conhecimento.versao}</span><Badge>{conhecimento.robustez_pct}% · {conhecimento.status}</Badge></div>
                <p className="text-muted-foreground">{conhecimento.conclusao}</p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(conhecimento.dimensoes_robustez).map(([dimensao, valor]) => (
                    <Badge key={dimensao} variant="outline">{dimensao.replaceAll("_", " ")}: {valor}%</Badge>
                  ))}
                </div>
                <div className="grid gap-1 sm:grid-cols-2">
                  {conhecimento.cobertura_criterios.map((criterio) => (
                    <div key={criterio.codigo} className="text-xs flex gap-2"><span>{criterio.atendido ? "✓" : "○"}</span><span>{criterio.codigo} · {criterio.descricao}</span></div>
                  ))}
                </div>
                {conhecimento.fontes_confirmadas.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-medium">Fontes jurídicas confirmadas</p>
                    {conhecimento.fontes_confirmadas.map((fonte) => (
                      <a key={`${fonte.codigo}-${fonte.dispositivo}`} href={fonte.url_oficial}
                        target="_blank" rel="noreferrer" className="block text-xs text-primary underline">
                        {fonte.referencia} · {fonte.dispositivo} · {fonte.orgao_emissor}
                      </a>
                    ))}
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" disabled={acao !== null || conhecimento.status === "aguardando_evidencia"}
                    onClick={() => executar(`conhecimento-${conhecimento.id}`, () => revisarConhecimentoPlano(contratacaoId, conhecimento.id, "aprovado"))}>Aprovar conhecimento</Button>
                  <Button size="sm" variant="outline" disabled={acao !== null}
                    onClick={() => executar(`conhecimento-${conhecimento.id}`, () => revisarConhecimentoPlano(contratacaoId, conhecimento.id, "rejeitado"))}>Rejeitar</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
      )}
    </Card>
  );
}
