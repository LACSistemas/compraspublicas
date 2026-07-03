"use client";

import { use, useState } from "react";
import { Loader2 } from "lucide-react";

import { AnaliseResultadoView } from "@/components/analise-resultado-view";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { dispararAnalise, getAnalise } from "@/lib/api-client";
import type { Analise } from "@/lib/types";
import { usePolling } from "@/lib/use-pesquisa-polling";

export default function AnalisePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const pesquisaId = Number(id);

  const [reiniciando, setReiniciando] = useState(false);
  const [erroReinicio, setErroReinicio] = useState<string | null>(null);

  const { data: analise, erro: erroPolling } = usePolling<Analise>({
    fetchFn: () => getAnalise(pesquisaId),
    intervalMs: 5000,
    shouldStop: (resultado) => resultado.status === "completo" || resultado.status === "erro",
  });

  async function tentarNovamente() {
    setErroReinicio(null);
    setReiniciando(true);
    try {
      await dispararAnalise(pesquisaId);
      window.location.reload();
    } catch (e) {
      setErroReinicio(e instanceof Error ? e.message : "Erro ao reiniciar análise.");
      setReiniciando(false);
    }
  }

  if (erroPolling) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertTitle>Erro ao consultar análise</AlertTitle>
          <AlertDescription>{erroPolling.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!analise || analise.status === "pendente" || analise.status === "em_andamento") {
    return (
      <div className="p-8">
        <Card>
          <CardContent className="flex items-center gap-3 py-6">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Analisando com IA...</span>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (analise.status === "erro") {
    return (
      <div className="flex flex-col gap-4 p-8">
        <Alert variant="destructive">
          <AlertTitle>A análise falhou</AlertTitle>
          <AlertDescription>{analise.erro_mensagem ?? "Erro desconhecido."}</AlertDescription>
        </Alert>
        {erroReinicio && (
          <Alert variant="destructive">
            <AlertDescription>{erroReinicio}</AlertDescription>
          </Alert>
        )}
        <Button onClick={tentarNovamente} disabled={reiniciando} className="self-start">
          {reiniciando ? "Reiniciando..." : "Tentar novamente"}
        </Button>
      </div>
    );
  }

  if (!analise.resultado) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertTitle>Resposta inesperada</AlertTitle>
          <AlertDescription>
            A análise foi concluída mas não retornou resultado.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-8">
      <AnaliseResultadoView resultado={analise.resultado} />
    </div>
  );
}
