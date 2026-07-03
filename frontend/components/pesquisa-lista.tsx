import Link from "next/link";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { Pesquisa, StatusPesquisa } from "@/lib/types";

const VARIANTE_POR_STATUS: Record<
  StatusPesquisa,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pendente: "outline",
  em_andamento: "secondary",
  completo: "default",
  erro: "destructive",
};

export function PesquisaLista({ pesquisas }: { pesquisas: Pesquisa[] }) {
  if (pesquisas.length === 0) {
    return <p className="text-sm text-muted-foreground">Nenhuma pesquisa ainda.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Termo</TableHead>
          <TableHead>Quantidade Desejada</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Data</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {pesquisas.map((pesquisa) => (
          <TableRow key={pesquisa.id}>
            <TableCell>{pesquisa.termo_busca}</TableCell>
            <TableCell>{pesquisa.quantidade_desejada ?? "—"}</TableCell>
            <TableCell>
              <Badge variant={VARIANTE_POR_STATUS[pesquisa.status]}>
                {pesquisa.status}
              </Badge>
            </TableCell>
            <TableCell>{new Date(pesquisa.criado_em).toLocaleString("pt-BR")}</TableCell>
            <TableCell>
              <Link href={`/pesquisas/${pesquisa.id}`} className="text-primary underline-offset-4 hover:underline">
                Ver
              </Link>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
