"use client";

import { AuthGuard } from "@/components/auth-guard";
import { ContratacaoForm } from "@/components/contratacao-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function NovaContratacaoPage() {
  return (
    <AuthGuard>
      <div className="flex flex-1 flex-col gap-6 p-8 max-w-2xl mx-auto w-full">
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Passo 1 de 5
          </p>
          <h1 className="text-2xl font-semibold">Nova Contratação</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Informe os dados básicos do processo. A IA irá gerar perguntas específicas para construir a base de conhecimento.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dados do Processo</CardTitle>
          </CardHeader>
          <CardContent>
            <ContratacaoForm />
          </CardContent>
        </Card>
      </div>
    </AuthGuard>
  );
}
