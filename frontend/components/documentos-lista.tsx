import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Processo } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

function slugDoProcesso(url: string): string {
  return url.replace(/\/+$/, "").split("/").pop() ?? "";
}

function montarUrlDownload(pesquisaId: number, slug: string, arquivo: string): string {
  const caminho = [slug, arquivo].map(encodeURIComponent).join("/");
  return `${API_URL}/pesquisas/${pesquisaId}/documentos/${caminho}`;
}

function formatarTamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentosLista({
  pesquisaId,
  processos,
}: {
  pesquisaId: number;
  processos: Processo[];
}) {
  const linhas = processos.flatMap((processo) => {
    const slug = slugDoProcesso(processo.url);
    return (processo.arquivos_baixados ?? []).map((arquivo) => {
      const metadado = processo.documentos?.find((d) => d.nome === arquivo.arquivo);
      return {
        chave: `${processo.url}/${arquivo.arquivo}`,
        numeroProcesso: processo.numero_processo,
        arquivo: arquivo.arquivo,
        tamanho: arquivo.tamanho_bytes,
        tipo: metadado?.tipo,
        data: metadado?.data,
        href: montarUrlDownload(pesquisaId, slug, arquivo.arquivo),
      };
    });
  });

  if (linhas.length === 0) {
    return <p className="text-sm text-muted-foreground">Nenhum documento baixado.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Processo</TableHead>
          <TableHead>Documento</TableHead>
          <TableHead>Tipo</TableHead>
          <TableHead>Data</TableHead>
          <TableHead>Tamanho</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {linhas.map((linha) => (
          <TableRow key={linha.chave}>
            <TableCell>{linha.numeroProcesso ?? "—"}</TableCell>
            <TableCell>{linha.arquivo}</TableCell>
            <TableCell>{linha.tipo ?? "—"}</TableCell>
            <TableCell>{linha.data ?? "—"}</TableCell>
            <TableCell>{formatarTamanho(linha.tamanho)}</TableCell>
            <TableCell>
              <a
                href={linha.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline-offset-4 hover:underline"
              >
                Baixar
              </a>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
