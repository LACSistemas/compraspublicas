"use client";

import Link from "next/link";
import { Clock } from "lucide-react";

export default function AguardandoPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="w-full max-w-sm text-center space-y-6">
        <div className="flex justify-center">
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-bold tracking-tight">
            LA
          </span>
        </div>

        <div className="flex justify-center">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-muted">
            <Clock className="size-7 text-muted-foreground" />
          </div>
        </div>

        <div className="space-y-2">
          <h1 className="text-xl font-bold text-foreground tracking-tight">
            Aguardando aprovação
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Sua conta foi criada com sucesso. O administrador precisa aprová-la antes que você possa acessar o sistema.
          </p>
        </div>

        <Link
          href="/login"
          className="inline-block text-sm text-primary font-medium hover:underline"
        >
          Voltar ao login
        </Link>
      </div>
    </div>
  );
}
