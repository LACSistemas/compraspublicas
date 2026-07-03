import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  AnaliseResultado,
  Classificacao,
  Constatacao,
  GrauRisco,
  ProcessoAuditado,
} from "@/lib/types";

// Mesma paleta da Seção 22 do prompt.md (padrão visual do relatório DOCX),
// pra manter consistência entre o webapp e o relatório exportado.
const COR_CLASSIFICACAO: Record<Classificacao, string> = {
  C: "bg-[#2e7d32] text-white",
  PC: "bg-[#b45309] text-white",
  NC: "bg-[#c62828] text-white",
  "N/A": "bg-[#6b7280] text-white",
};

const COR_RISCO: Record<GrauRisco, string> = {
  Baixo: "bg-[#2e7d32] text-white",
  Médio: "bg-[#b45309] text-white",
  Alto: "bg-[#c2410c] text-white",
  Crítico: "bg-[#991b1b] text-white",
};

function CardSintese({ titulo, valor }: { titulo: string; valor: string | number }) {
  return (
    <Card size="sm" className="min-w-32 flex-1">
      <CardContent className="flex flex-col gap-1 py-2">
        <span className="text-xs text-muted-foreground">{titulo}</span>
        <span className="text-xl font-semibold">{valor}</span>
      </CardContent>
    </Card>
  );
}

function ListaSimples({ titulo, itens }: { titulo: string; itens: string[] }) {
  if (itens.length === 0) return null;
  return (
    <div>
      <h4 className="mb-1 text-sm font-medium">{titulo}</h4>
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
        {itens.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function ConstatacaoItem({ constatacao, indice }: { constatacao: Constatacao; indice: number }) {
  return (
    <AccordionItem value={`constatacao-${indice}`}>
      <AccordionTrigger>
        <div className="flex flex-1 items-center justify-between gap-2 pr-2">
          <span>{constatacao.descricao_sumaria}</span>
          <div className="flex shrink-0 gap-1.5">
            <Badge className={COR_CLASSIFICACAO[constatacao.classificacao]}>
              {constatacao.classificacao}
            </Badge>
            <Badge className={COR_RISCO[constatacao.risco]}>{constatacao.risco}</Badge>
          </div>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="flex flex-col gap-3 text-sm">
          <div>
            <h5 className="mb-1 font-medium">Situação encontrada</h5>
            <p className="whitespace-pre-wrap text-muted-foreground">
              {constatacao.situacao_encontrada}
            </p>
          </div>
          <div>
            <h5 className="mb-1 font-medium">Recomendação</h5>
            <p className="text-muted-foreground">{constatacao.recomendacao}</p>
          </div>
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

function ProcessoAuditadoView({ processo }: { processo: ProcessoAuditado }) {
  const { metadados, quadro_sintese } = processo;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>
            {metadados.numero_processo ?? "Processo"} — {metadados.modalidade ?? "—"}
          </CardTitle>
          <CardDescription>{metadados.objeto ?? "Objeto não informado."}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-1 text-sm sm:grid-cols-2">
          <p>
            <span className="font-medium">Órgão:</span> {metadados.orgao ?? "—"}
          </p>
          <p>
            <span className="font-medium">Município/UF:</span> {metadados.municipio_uf ?? "—"}
          </p>
          <p>
            <span className="font-medium">Critério de julgamento:</span>{" "}
            {metadados.criterio_julgamento ?? "—"}
          </p>
          <p>
            <span className="font-medium">Valor estimado:</span> {metadados.valor_estimado ?? "—"}
          </p>
          <p>
            <span className="font-medium">Situação:</span> {metadados.situacao ?? "—"}
          </p>
          <p>
            <span className="font-medium">Natureza do objeto:</span>{" "}
            {metadados.natureza_objeto ?? "—"}
          </p>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <CardSintese titulo="Total de itens" valor={quadro_sintese.total_itens} />
        <CardSintese titulo="Conformes" valor={quadro_sintese.conformes} />
        <CardSintese
          titulo="Parcialmente conformes"
          valor={quadro_sintese.parcialmente_conformes}
        />
        <CardSintese titulo="Não conformes" valor={quadro_sintese.nao_conformes} />
        <CardSintese titulo="% Conformidade" valor={quadro_sintese.percentual_conformidade} />
        <CardSintese titulo="Risco geral" valor={quadro_sintese.grau_risco_geral} />
      </div>

      {processo.classificacao_checklist.length > 0 && (
        <div>
          <h3 className="mb-2 text-base font-semibold">Checklist de auditoria</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Descrição</TableHead>
                <TableHead>Classificação</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {processo.classificacao_checklist.map((linha, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium text-muted-foreground">
                    {linha.item}
                  </TableCell>
                  <TableCell>{linha.descricao}</TableCell>
                  <TableCell>
                    <Badge className={COR_CLASSIFICACAO[linha.classificacao]}>
                      {linha.classificacao}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {processo.constatacoes.length > 0 && (
        <div>
          <h3 className="mb-2 text-base font-semibold">Constatações</h3>
          <Accordion>
            {processo.constatacoes.map((constatacao, i) => (
              <ConstatacaoItem key={i} constatacao={constatacao} indice={i} />
            ))}
          </Accordion>
        </div>
      )}

      <ListaSimples titulo="Documentos ausentes" itens={processo.documentos_ausentes} />
      <ListaSimples titulo="Dicas de aprimoramento" itens={processo.dicas_aprimoramento} />
      <ListaSimples
        titulo="Recomendações consolidadas"
        itens={processo.recomendacoes_consolidadas}
      />
    </div>
  );
}

export function AnaliseResultadoView({ resultado }: { resultado: AnaliseResultado }) {
  const processos = resultado.processos_auditados ?? [];

  if (processos.length === 0) {
    return (
      <Alert>
        <AlertTitle>Nenhum processo auditado</AlertTitle>
        <AlertDescription>A análise não retornou nenhum processo.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {processos.map((processo, i) => (
        <ProcessoAuditadoView key={processo.url ?? i} processo={processo} />
      ))}
    </div>
  );
}
