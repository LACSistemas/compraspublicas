import Link from "next/link";

import { Button } from "@/components/ui/button";
import { PesquisaLista } from "@/components/pesquisa-lista";
import { listarPesquisas } from "@/lib/api-client";

export default async function PesquisasPage() {
  const pesquisas = await listarPesquisas();

  return (
    <div className="flex flex-1 flex-col gap-6 p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Pesquisas</h1>
        <Button render={<Link href="/nova-pesquisa">Nova Pesquisa</Link>} />
      </div>
      <PesquisaLista pesquisas={pesquisas} />
    </div>
  );
}
