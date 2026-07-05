"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, Download, FileText, Loader2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { gerarETP, getGeracaoETP, getUrlDownloadETP } from "@/lib/api-client";
import type { Geracao, StatusGeracao } from "@/lib/types";

interface Props {
  pesquisaId: number;
}

export function EtpGeracaoCard({ pesquisaId }: Props) {
  const [geracao, setGeracao] = useState<Geracao | null>(null);
  const [carregandoStatus, setCarregandoStatus] = useState(true);
  const [disparando, setDisparando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tipo, setTipo] = useState<"etp" | "tr">("etp");
  const [unGestora, setUnGestora] = useState("");
  const [responsaveis, setResponsaveis] = useState("");
  const [objetoResumido, setObjetoResumido] = useState("");

  useEffect(() => {
    getGeracaoETP(pesquisaId, tipo)
      .then(setGeracao)
      .catch(() => setGeracao(null))
      .finally(() => setCarregandoStatus(false));
  }, [pesquisaId, tipo]);

  useEffect(() => {
    if (!geracao || geracao.status === "completo" || geracao.status === "erro") return;
    const interval = setInterval(() => {
      getGeracaoETP(pesquisaId, geracao.tipo)
        .then(setGeracao)
        .catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [geracao, pesquisaId]);

  async function handleGerar() {
    if (!unGestora.trim() || !responsaveis.trim()) {
      setErro("Preencha Unidade Gestora e Responsáveis.");
      return;
    }
    setErro(null);
    setDisparando(true);
    try {
      await gerarETP(pesquisaId, {
        tipo,
        un_gestora: unGestora,
        responsaveis,
        objeto_resumido: objetoResumido || null,
      });
      const novaGeracao = await getGeracaoETP(pesquisaId, tipo);
      setGeracao(novaGeracao);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao iniciar geração.");
    } finally {
      setDisparando(false);
    }
  }

  const emAndamento =
    geracao && (geracao.status === "pendente" || geracao.status === "em_andamento");
  const completo = geracao?.status === "completo";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="size-5" />
          Gerar Documento (ETP / TR)
        </CardTitle>
        <CardDescription>
          Geração assistida de rascunho fundamentado nas fontes legais (Lei 14.133/2021 e Decreto
          5352-R/2023).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Alert className="border-amber-500 bg-amber-50 text-amber-900">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            <strong>Rascunho para revisão humana.</strong> Confira e complete os campos{" "}
            <code>[A PREENCHER PELO AGENTE]</code> antes de entregar.
          </AlertDescription>
        </Alert>

        {!emAndamento && !completo && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="tipo-doc">Tipo de documento</Label>
              <select
                id="tipo-doc"
                value={tipo}
                onChange={(e) => setTipo(e.target.value as "etp" | "tr")}
                className="w-48 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm"
              >
                <option value="etp">ETP — Estudo Técnico Preliminar</option>
                <option value="tr">TR — Termo de Referência (minuta)</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="un-gestora">Unidade Gestora *</Label>
              <Input
                id="un-gestora"
                placeholder="Ex.: SESA — Secretaria da Saúde"
                value={unGestora}
                onChange={(e) => setUnGestora(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="responsaveis">Responsável(is) *</Label>
              <Input
                id="responsaveis"
                placeholder="Ex.: João Silva, Analista de Compras"
                value={responsaveis}
                onChange={(e) => setResponsaveis(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="objeto">Objeto resumido (opcional)</Label>
              <Input
                id="objeto"
                placeholder="Ex.: Aquisição de medicamentos (Ibuprofeno 300mg)"
                value={objetoResumido}
                onChange={(e) => setObjetoResumido(e.target.value)}
              />
            </div>
            {erro && (
              <Alert variant="destructive">
                <AlertDescription>{erro}</AlertDescription>
              </Alert>
            )}
            <Button onClick={handleGerar} disabled={disparando} className="self-start">
              {disparando ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Iniciando...
                </>
              ) : (
                `Gerar ${tipo.toUpperCase()} (rascunho)`
              )}
            </Button>
          </div>
        )}

        {emAndamento && (
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Gerando {geracao?.tipo.toUpperCase()}... aguarde.
            <GeracaoBadge status={geracao.status} />
          </div>
        )}

        {completo && geracao && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-sm font-medium text-green-700">
              <CheckCircle className="size-4" />
              {geracao.tipo.toUpperCase()} gerado.
              <GeracaoBadge status={geracao.status} />
            </div>

            {geracao.pendencias && geracao.pendencias.length > 0 && (
              <div>
                <p className="mb-1 text-sm font-medium">Pendências para revisão:</p>
                <ul className="list-inside list-disc space-y-0.5 text-sm text-muted-foreground">
                  {geracao.pendencias.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            )}

            {geracao.arquivo_disponivel && (
              <a
                href={getUrlDownloadETP(pesquisaId, geracao.tipo)}
                download
                className="self-start"
              >
                <Button variant="outline" className="gap-2">
                  <Download className="size-4" />
                  Baixar {geracao.tipo.toUpperCase()} (.docx)
                </Button>
              </a>
            )}

            <Button
              variant="ghost"
              size="sm"
              className="self-start text-muted-foreground"
              onClick={() => {
                setGeracao(null);
                setCarregandoStatus(false);
              }}
            >
              Gerar novo
            </Button>
          </div>
        )}

        {geracao?.status === "erro" && (
          <Alert variant="destructive">
            <AlertDescription>
              Erro na geração: {geracao.erro_mensagem}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

function GeracaoBadge({ status }: { status: StatusGeracao }) {
  const cores: Record<StatusGeracao, string> = {
    pendente: "bg-yellow-100 text-yellow-800",
    em_andamento: "bg-blue-100 text-blue-800",
    completo: "bg-green-100 text-green-800",
    erro: "bg-red-100 text-red-800",
  };
  const rotulos: Record<StatusGeracao, string> = {
    pendente: "Pendente",
    em_andamento: "Em andamento",
    completo: "Completo",
    erro: "Erro",
  };
  return (
    <Badge variant="outline" className={cores[status]}>
      {rotulos[status]}
    </Badge>
  );
}
