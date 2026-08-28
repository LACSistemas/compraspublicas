"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { getPerguntas, responderPergunta, processarBase } from "@/lib/api-client";
import type { PerguntaContratacao } from "@/lib/types";
import { PesquisaPrecosCard } from "@/components/pesquisa-precos-card";

interface Props {
  perguntas: PerguntaContratacao[];
  contratacaoId: number;
  onProcessarIniciado: () => void;
}

export function InvestigacaoFlow({ perguntas, contratacaoId, onProcessarIniciado }: Props) {
  const [perguntasAtuais, setPerguntasAtuais] = useState(perguntas);
  const [respostas, setRespostas] = useState<Record<number, string>>(() => {
    const init: Record<number, string> = {};
    for (const p of perguntasAtuais) {
      if (p.resposta_escolhida) init[p.id] = p.resposta_escolhida;
    }
    return init;
  });

  const primeiroSemResposta = perguntasAtuais.findIndex((p) => !respostas[p.id]);
  const [currentIdx, setCurrentIdx] = useState(
    primeiroSemResposta === -1 ? perguntasAtuais.length : primeiroSemResposta,
  );
  const [respondendo, setRespondendo] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const todasRespondidas = currentIdx >= perguntasAtuais.length;
  const perguntaAtual = todasRespondidas ? null : perguntasAtuais[currentIdx];
  const progresso = perguntasAtuais.length
    ? (Object.keys(respostas).length / perguntasAtuais.length) * 100 : 0;

  async function handleResposta(letra: string) {
    if (!perguntaAtual || respondendo) return;
    setErro(null);
    setRespondendo(true);
    try {
      await responderPergunta(contratacaoId, perguntaAtual.id, letra);
      setRespostas((prev) => ({ ...prev, [perguntaAtual.id]: letra }));
      setCurrentIdx((i) => i + 1);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao registrar resposta");
    } finally {
      setRespondendo(false);
    }
  }

  async function handleProcessar() {
    setErro(null);
    setProcessando(true);
    try {
      const resultado = await processarBase(contratacaoId);
      if (resultado.perguntas_adicionais) {
        const atualizadas = await getPerguntas(contratacaoId);
        setPerguntasAtuais(atualizadas);
        setCurrentIdx(atualizadas.findIndex((p) => !p.resposta_escolhida));
        setAviso(`${resultado.perguntas_adicionais} pergunta(s) complementar(es) foram adicionadas para fechar pendências importantes.`);
        setProcessando(false);
      } else {
        onProcessarIniciado();
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao iniciar processamento");
      setProcessando(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto w-full">
      {/* Progresso geral */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {todasRespondidas
              ? "Todas as perguntas respondidas"
              : `Pergunta ${currentIdx + 1} de ${perguntasAtuais.length}`}
          </span>
          <span className="font-medium">{Math.round(progresso)}%</span>
        </div>
        <Progress value={progresso} />
      </div>

      {erro && (
        <Alert variant="destructive">
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      )}
      {aviso && (
        <Alert><AlertDescription>{aviso}</AlertDescription></Alert>
      )}

      {/* Pergunta atual */}
      {perguntaAtual && (
        <Card>
          <CardHeader>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Pergunta {currentIdx + 1}
            </p>
            <CardTitle className="text-base leading-snug">{perguntaAtual.texto}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {perguntaAtual.alternativas.map((alt) => (
              <button
                key={alt.letra}
                onClick={() => handleResposta(alt.letra)}
                disabled={respondendo}
                className={[
                  "flex items-start gap-3 rounded-lg border px-4 py-3 text-sm text-left transition-colors",
                  "border-border hover:bg-muted hover:border-muted-foreground/40",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  "focus-visible:outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
                ].join(" ")}
              >
                <span className="flex-shrink-0 w-5 h-5 rounded-full border-2 border-muted-foreground/50 flex items-center justify-center text-xs font-bold text-muted-foreground uppercase">
                  {alt.letra}
                </span>
                <span>{alt.texto}</span>
              </button>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Perguntas já respondidas (somente leitura — navegar para ver) */}
      {currentIdx > 0 && !todasRespondidas && (
        <div className="flex gap-2 flex-wrap">
          {perguntasAtuais.slice(0, currentIdx).map((p, idx) => {
            const resposta = respostas[p.id];
            return (
              <button
                key={p.id}
                onClick={() => setCurrentIdx(idx)}
                className="h-6 w-6 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400 text-xs font-medium hover:opacity-80"
                title={`Pergunta ${idx + 1}: (${resposta})`}
              >
                {idx + 1}
              </button>
            );
          })}
        </div>
      )}

      {/* Todas respondidas → processar */}
      {todasRespondidas && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="pt-6 flex flex-col gap-4">
            <div>
              <p className="font-semibold text-foreground">
                Investigação concluída!
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Você respondeu as {perguntasAtuais.length} perguntas desta etapa. Agora vamos verificar se alguma informação essencial ainda precisa de confirmação antes de construir a Base de Conhecimento.
              </p>
            </div>
            <PesquisaPrecosCard contratacaoId={contratacaoId} />
            <Button
              onClick={handleProcessar}
              disabled={processando}
              size="lg"
            >
              {processando ? "Verificando pendências…" : "Verificar pendências e continuar"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
