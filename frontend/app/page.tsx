import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 bg-zinc-50 p-8 text-center dark:bg-black">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Auditoria de Compras Públicas
        </h1>
        <p className="max-w-md text-muted-foreground">
          Pesquise processos licitatórios, baixe os documentos e gere um
          relatório de auditoria automatizado.
        </p>
      </div>
      <div className="flex flex-col gap-4 sm:flex-row">
        <Button size="lg" render={<Link href="/nova-pesquisa">Nova Pesquisa</Link>} />
        <Button
          size="lg"
          variant="outline"
          render={<Link href="/pesquisas">Ver Pesquisas</Link>}
        />
      </div>
    </div>
  );
}
