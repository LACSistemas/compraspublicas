"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { getPesquisaPrecos } from "@/lib/api-client";
import type { CampanhaPesquisaPrecos } from "@/lib/types";

export function PesquisaPrecosCard({ contratacaoId }: { contratacaoId: number }) {
  const [campanha, setCampanha] = useState<CampanhaPesquisaPrecos | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const carregar = useCallback(async () => {
    try { setCampanha(await getPesquisaPrecos(contratacaoId)); setErro(null); }
    catch (e) {
      const mensagem = e instanceof Error ? e.message : "Falha ao consultar a pesquisa";
      if (!mensagem.includes("Pesquisa de preços não iniciada")) setErro(mensagem);
    }
  }, [contratacaoId]);
  useEffect(() => {
    const inicial = window.setTimeout(() => void carregar(), 0);
    const intervalo = window.setInterval(() => void carregar(), 3000);
    return () => { window.clearTimeout(inicial); window.clearInterval(intervalo); };
  }, [carregar]);
  const concluidas = campanha?.consultas.filter((consulta) => consulta.status === "completa").length ?? 0;
  const total = campanha?.consultas.length || 5;
  const pronta = campanha?.status === "pronta_revisao" || campanha?.status === "aprovada";
  const progresso = pronta ? 100 : 100 * concluidas / Math.max(1, total);
  return (
    <div className="rounded-lg border bg-background p-4 space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">Pesquisa de mercado em segundo plano</span>
        <span className="text-muted-foreground">{Math.round(progresso)}%</span>
      </div>
      <Progress value={progresso} />
      <p className="text-xs text-muted-foreground">
        {!campanha ? "Preparando as buscas do objeto…" : pronta
          ? `${campanha.resultado.amostra_tratada ?? campanha.resultado.amostra ?? 0} preço(s) comparável(is) já podem alimentar a Base de Conhecimento.`
          : `${concluidas} de ${total} buscas concluídas. Você pode esperar mais um pouco ou continuar agora.`}
      </p>
      {campanha?.status === "erro" && <Alert variant="destructive"><AlertDescription>
        A pesquisa externa encontrou uma falha, mas suas respostas foram preservadas. O retry continuará em segundo plano: {campanha.erro_mensagem}
      </AlertDescription></Alert>}
      {erro && <p className="text-xs text-destructive">Não foi possível atualizar o progresso: {erro}</p>}
    </div>
  );
}
