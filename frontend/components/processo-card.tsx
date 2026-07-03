import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Processo } from "@/lib/types";

function TabelaChaveValor({ dados }: { dados?: Record<string, string> }) {
  const entradas = Object.entries(dados ?? {});
  if (entradas.length === 0) return null;

  return (
    <Table>
      <TableBody>
        {entradas.map(([chave, valor]) => (
          <TableRow key={chave}>
            <TableCell className="font-medium text-muted-foreground">{chave}</TableCell>
            <TableCell>{valor}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function ProcessoCard({ processo }: { processo: Processo }) {
  const itens = processo.itens ?? [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>Processo {processo.numero_processo ?? "—"}</CardTitle>
          {processo.situacao && <Badge variant="outline">{processo.situacao}</Badge>}
        </div>
        <CardDescription>{processo.comprador ?? "Comprador não identificado"}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid gap-1 text-sm">
          <p>
            <span className="font-medium">Modalidade:</span> {processo.modalidade ?? "—"}
          </p>
          <p>
            <span className="font-medium">Objeto:</span> {processo.objeto ?? "—"}
          </p>
        </div>

        {processo.informacoes && Object.keys(processo.informacoes).length > 0 && (
          <div>
            <h4 className="mb-1 text-sm font-medium">Informações</h4>
            <TabelaChaveValor dados={processo.informacoes} />
          </div>
        )}

        {processo.datas && Object.keys(processo.datas).length > 0 && (
          <div>
            <h4 className="mb-1 text-sm font-medium">Datas</h4>
            <TabelaChaveValor dados={processo.datas} />
          </div>
        )}

        {itens.length > 0 && (
          <div>
            <h4 className="mb-1 text-sm font-medium">Itens</h4>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nº</TableHead>
                  <TableHead>Descrição</TableHead>
                  <TableHead>Quantidade</TableHead>
                  <TableHead>Unidade</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {itens.map((item, i) => (
                  <TableRow key={i}>
                    <TableCell>{item.numero ?? "—"}</TableCell>
                    <TableCell>{item.descricao ?? "—"}</TableCell>
                    <TableCell>{item.quantidade ?? "—"}</TableCell>
                    <TableCell>{item.unidade ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
