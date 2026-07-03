import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { Processo } from "@/lib/types";

export function ConteudoBrutoViewer({ processos }: { processos: Processo[] }) {
  return (
    <Accordion>
      {processos.map((processo, i) => (
        <AccordionItem key={processo.url ?? i} value={processo.url ?? String(i)}>
          <AccordionTrigger>
            Processo {processo.numero_processo ?? i + 1}
          </AccordionTrigger>
          <AccordionContent>
            <pre className="max-h-96 overflow-auto rounded-lg bg-muted p-3 text-xs whitespace-pre-wrap">
              {(processo.conteudo_bruto ?? []).join("\n")}
            </pre>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
