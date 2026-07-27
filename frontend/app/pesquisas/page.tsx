"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Button } from "@/components/ui/button";
import { PesquisaLista } from "@/components/pesquisa-lista";
import { listarPesquisas } from "@/lib/api-client";
import type { Pesquisa } from "@/lib/types";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function PesquisasPage() {
  return (
    <AuthGuard>
      <PesquisasContent />
    </AuthGuard>
  );
}

function PesquisasContent() {
  const [pesquisas, setPesquisas] = useState<Pesquisa[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    listarPesquisas()
      .then(setPesquisas)
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar pesquisas"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Pesquisas</h1>
        <Button render={<Link href="/nova-pesquisa">Nova Pesquisa</Link>} />
      </div>
      {loading && <p className="text-sm text-muted-foreground">Carregando...</p>}
      {erro && <p className="text-sm text-destructive">{erro}</p>}
      {!loading && !erro && <PesquisaLista pesquisas={pesquisas} />}
    </div>
  );
}
