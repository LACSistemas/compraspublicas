import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PesquisaForm } from "@/components/pesquisa-form";

export default function NovaPesquisaPage() {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Nova Pesquisa</CardTitle>
          <CardDescription>
            Busque processos de compras públicas por termo e, opcionalmente,
            informe a quantidade desejada para refinar a auditoria.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PesquisaForm />
        </CardContent>
      </Card>
    </div>
  );
}
