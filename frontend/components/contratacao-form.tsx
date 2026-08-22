"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { criarContratacao } from "@/lib/api-client";

const TIPOS = ["Compras", "Serviços", "Obras", "Serviços de Engenharia", "Outros"];

export function ContratacaoForm() {
  const router = useRouter();
  const [objeto, setObjeto] = useState("");
  const [orgao, setOrgao] = useState("");
  const [processo, setProcesso] = useState("");
  const [equipe, setEquipe] = useState("");
  const [tipo, setTipo] = useState("");
  const [contexto, setContexto] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const c = await criarContratacao({
        objeto,
        orgao_unidade: orgao,
        numero_processo: processo || undefined,
        equipe_responsavel: equipe || undefined,
        tipo_contratacao: tipo || undefined,
        contexto_inicial: contexto || undefined,
      });
      router.push(`/contratacoes/${c.id}`);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao criar contratação.");
      setCarregando(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="objeto">O que você deseja contratar? *</Label>
        <Textarea
          id="objeto"
          placeholder="ex: Compra de ambulância Tipo Suporte Básico (B)"
          value={objeto}
          onChange={(e) => setObjeto(e.target.value)}
          required
          disabled={carregando}
          rows={3}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="orgao">Órgão / Unidade *</Label>
        <Input
          id="orgao"
          placeholder="ex: Secretaria Municipal de Saúde"
          value={orgao}
          onChange={(e) => setOrgao(e.target.value)}
          required
          disabled={carregando}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="processo">Número do Processo / DFD</Label>
          <Input
            id="processo"
            placeholder="ex: DFD 128/2025"
            value={processo}
            onChange={(e) => setProcesso(e.target.value)}
            disabled={carregando}
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="tipo">Tipo de Contratação</Label>
          <select
            id="tipo"
            value={tipo}
            onChange={(e) => setTipo(e.target.value)}
            disabled={carregando}
            className="h-8 rounded-lg border border-input bg-background px-2.5 text-sm focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 outline-none"
          >
            <option value="">Selecione…</option>
            {TIPOS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="equipe">Equipe Responsável</Label>
        <Input
          id="equipe"
          placeholder="ex: João da Silva, Maria Souza"
          value={equipe}
          onChange={(e) => setEquipe(e.target.value)}
          disabled={carregando}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="contexto">Contexto Inicial</Label>
        <Textarea
          id="contexto"
          placeholder="Descreva brevemente o contexto desta contratação, urgências ou restrições relevantes…"
          value={contexto}
          onChange={(e) => setContexto(e.target.value)}
          disabled={carregando}
          rows={4}
        />
      </div>

      {erro && (
        <Alert variant="destructive">
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" disabled={carregando || !objeto || !orgao} size="lg">
        {carregando ? "Criando…" : "Criar Contratação"}
      </Button>
    </form>
  );
}
