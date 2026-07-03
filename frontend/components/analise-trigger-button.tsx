"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { dispararAnalise, getAnalise } from "@/lib/api-client";

export function AnaliseTriggerButton({ pesquisaId }: { pesquisaId: number }) {
  const router = useRouter();
  const [carregando, setCarregando] = useState(false);
  const [verificando, setVerificando] = useState(true);
  const [emAndamento, setEmAndamento] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    getAnalise(pesquisaId)
      .then((analise) => {
        setEmAndamento(analise.status === "pendente" || analise.status === "em_andamento");
      })
      .catch(() => {
        // Nenhuma análise existente ainda (404) — segue normal.
      })
      .finally(() => setVerificando(false));
  }, [pesquisaId]);

  async function handleClick() {
    if (emAndamento) {
      router.push(`/pesquisas/${pesquisaId}/analise`);
      return;
    }

    setErro(null);
    setCarregando(true);
    try {
      await dispararAnalise(pesquisaId);
      router.push(`/pesquisas/${pesquisaId}/analise`);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao iniciar análise.");
      setCarregando(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <Button onClick={handleClick} disabled={carregando || verificando}>
        {carregando
          ? "Iniciando..."
          : emAndamento
            ? "Ver análise em andamento"
            : "Condensar e enviar pra LLM"}
      </Button>
      {erro && (
        <Alert variant="destructive" className="max-w-sm">
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
