"use client";

import Link from "next/link";

export default function AguardandoPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-sm text-center space-y-4">
        <div className="text-4xl">⏳</div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          Conta aguardando aprovação
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Sua conta foi criada com sucesso. O administrador precisa aprová-la antes que você possa
          acessar o sistema.
        </p>
        <Link
          href="/login"
          className="inline-block mt-4 text-sm text-blue-600 hover:underline"
        >
          Voltar ao login
        </Link>
      </div>
    </div>
  );
}
