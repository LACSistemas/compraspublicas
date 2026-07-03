import { Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import type { StatusPesquisa } from "@/lib/types";

const TEXTO_STATUS: Record<StatusPesquisa, string> = {
  pendente: "Pesquisa na fila, aguardando início...",
  em_andamento: "Buscando processos e baixando documentos...",
  completo: "Pesquisa completa.",
  erro: "A pesquisa falhou.",
};

export function PesquisaStatusCard({
  status,
  erroMensagem,
}: {
  status: StatusPesquisa;
  erroMensagem?: string | null;
}) {
  if (status === "erro") {
    return (
      <Alert variant="destructive">
        <AlertTitle>Erro na pesquisa</AlertTitle>
        <AlertDescription>{erroMensagem ?? "Erro desconhecido."}</AlertDescription>
      </Alert>
    );
  }

  return (
    <Card>
      <CardContent className="flex items-center gap-3 py-6">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">{TEXTO_STATUS[status]}</span>
      </CardContent>
    </Card>
  );
}
