"use client";

import { use, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { AnaliseTriggerButton } from "@/components/analise-trigger-button";
import { EtpGeracaoCard } from "@/components/etp-geracao-card";
import { ConteudoBrutoViewer } from "@/components/conteudo-bruto-viewer";
import { DocumentosLista } from "@/components/documentos-lista";
import { PesquisaStatusCard } from "@/components/pesquisa-status-card";
import { ProcessoCard } from "@/components/processo-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getPesquisa, getPesquisaStatus } from "@/lib/api-client";
import type { Pesquisa, PesquisaDetalhe } from "@/lib/types";
import { usePolling } from "@/lib/use-pesquisa-polling";

export default function PesquisaDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const pesquisaId = Number(id);

  const { data: status, erro: erroPolling } = usePolling<Pesquisa>({
    fetchFn: () => getPesquisaStatus(pesquisaId),
    intervalMs: 3000,
    shouldStop: (resultado) => resultado.status === "completo" || resultado.status === "erro",
  });

  const [detalhe, setDetalhe] = useState<PesquisaDetalhe | null>(null);
  const [erroDetalhe, setErroDetalhe] = useState<Error | null>(null);

  useEffect(() => {
    if (status?.status !== "completo") return;
    getPesquisa(pesquisaId)
      .then(setDetalhe)
      .catch((e) => setErroDetalhe(e instanceof Error ? e : new Error(String(e))));
  }, [status?.status, pesquisaId]);

  if (erroPolling) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertTitle>Erro ao consultar status da pesquisa</AlertTitle>
          <AlertDescription>{erroPolling.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
        Carregando...
      </div>
    );
  }

  if (status.status === "erro") {
    return (
      <div className="p-8">
        <PesquisaStatusCard status="erro" erroMensagem={status.erro_mensagem} />
      </div>
    );
  }

  if (status.status !== "completo") {
    return (
      <div className="p-8">
        <PesquisaStatusCard status={status.status} />
      </div>
    );
  }

  if (erroDetalhe) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar dados da pesquisa</AlertTitle>
          <AlertDescription>{erroDetalhe.message}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!detalhe) {
    return (
      <div className="p-8">
        <Card>
          <CardContent className="flex items-center gap-3 py-6">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Carregando dados completos...
            </span>
          </CardContent>
        </Card>
      </div>
    );
  }

  const processos = detalhe.resultado?.processos ?? [];

  return (
    <div className="flex flex-col gap-6 p-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Pesquisa: {detalhe.termo_busca}</h1>
          {detalhe.quantidade_desejada && (
            <p className="text-sm text-muted-foreground">
              Quantidade desejada: {detalhe.quantidade_desejada}
            </p>
          )}
        </div>
        <AnaliseTriggerButton pesquisaId={pesquisaId} />
      </div>

      <EtpGeracaoCard pesquisaId={pesquisaId} />

      <Tabs defaultValue="dados-organizados">
        <TabsList>
          <TabsTrigger value="dados-organizados">Dados Organizados</TabsTrigger>
          <TabsTrigger value="dados-brutos">Dados Brutos</TabsTrigger>
          <TabsTrigger value="documentos">Documentos</TabsTrigger>
        </TabsList>
        <TabsContent value="dados-organizados">
          <div className="flex flex-col gap-4 pt-4">
            {processos.map((processo, i) => (
              <ProcessoCard key={processo.url ?? i} processo={processo} />
            ))}
          </div>
        </TabsContent>
        <TabsContent value="dados-brutos">
          <div className="pt-4">
            <ConteudoBrutoViewer processos={processos} />
          </div>
        </TabsContent>
        <TabsContent value="documentos">
          <div className="pt-4">
            <DocumentosLista pesquisaId={pesquisaId} processos={processos} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
