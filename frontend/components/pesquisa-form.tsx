"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { criarPesquisa } from "@/lib/api-client";

export function PesquisaForm() {
  const router = useRouter();
  const [termoBusca, setTermoBusca] = useState("");
  const [quantidadeDesejada, setQuantidadeDesejada] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const pesquisa = await criarPesquisa({
        termo_busca: termoBusca,
        quantidade_desejada: quantidadeDesejada || null,
      });
      router.push(`/pesquisas/${pesquisa.id}`);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao criar pesquisa.");
      setCarregando(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="termo_busca">Termo de busca</Label>
        <Input
          id="termo_busca"
          placeholder="ex: cafe"
          value={termoBusca}
          onChange={(e) => setTermoBusca(e.target.value)}
          required
          disabled={carregando}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="quantidade_desejada">Quantidade desejada (opcional)</Label>
        <Textarea
          id="quantidade_desejada"
          placeholder="ex: 2 toneladas"
          value={quantidadeDesejada}
          onChange={(e) => setQuantidadeDesejada(e.target.value)}
          disabled={carregando}
        />
      </div>

      {erro && (
        <Alert variant="destructive">
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" disabled={carregando || !termoBusca}>
        {carregando ? "Iniciando..." : "Iniciar Pesquisa"}
      </Button>
    </form>
  );
}
