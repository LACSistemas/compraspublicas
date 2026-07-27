"use client";

import { AuthGuard } from "@/components/auth-guard";
import {
  adminAtivar,
  adminDashboard,
  adminDesativar,
  adminListarUsuarios,
  type AdminDashboard,
  type AdminUsuario,
} from "@/lib/api-client";
import { useEffect, useState } from "react";

export default function AdminPage() {
  return (
    <AuthGuard requireOwner>
      <AdminPanel />
    </AuthGuard>
  );
}

function AdminPanel() {
  const [aba, setAba] = useState<"usuarios" | "dashboard">("usuarios");

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            Painel de Administração
          </h1>
          <a href="/" className="text-sm text-blue-600 hover:underline">
            Voltar ao sistema
          </a>
        </div>

        <div className="flex gap-2 border-b border-gray-200 dark:border-gray-800">
          {(["usuarios", "dashboard"] as const).map((a) => (
            <button
              key={a}
              onClick={() => setAba(a)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                aba === a
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              {a === "usuarios" ? "Usuários" : "Dashboard de Tokens"}
            </button>
          ))}
        </div>

        {aba === "usuarios" ? <TabelaUsuarios /> : <DashboardTokens />}
      </div>
    </div>
  );
}

function TabelaUsuarios() {
  const [usuarios, setUsuarios] = useState<AdminUsuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    adminListarUsuarios()
      .then(setUsuarios)
      .catch((e) => setErro(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function toggle(u: AdminUsuario) {
    try {
      const updated = u.is_active ? await adminDesativar(u.id) : await adminAtivar(u.id);
      setUsuarios((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Erro");
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>;
  if (erro) return <p className="text-sm text-red-500">{erro}</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
      <table className="w-full text-sm">
        <thead className="bg-gray-100 dark:bg-gray-900">
          <tr>
            {["Nome", "E-mail", "Status", "Tokens", "Cadastro", ""].map((h) => (
              <th key={h} className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {usuarios.map((u) => (
            <tr key={u.id} className="bg-white dark:bg-gray-950">
              <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                {u.nome}
                {u.is_owner && (
                  <span className="ml-2 rounded bg-yellow-100 dark:bg-yellow-900 px-1.5 py-0.5 text-xs text-yellow-800 dark:text-yellow-200">
                    owner
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{u.email}</td>
              <td className="px-4 py-3">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                    u.is_active
                      ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                      : "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300"
                  }`}
                >
                  {u.is_active ? "Ativo" : "Aguardando"}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-600 dark:text-gray-400 tabular-nums">
                {u.tokens_total.toLocaleString("pt-BR")}
              </td>
              <td className="px-4 py-3 text-gray-500 dark:text-gray-500 text-xs">
                {u.criado_em ? new Date(u.criado_em).toLocaleDateString("pt-BR") : "—"}
              </td>
              <td className="px-4 py-3">
                {!u.is_owner && (
                  <button
                    onClick={() => toggle(u)}
                    className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                      u.is_active
                        ? "bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-300"
                        : "bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-300"
                    }`}
                  >
                    {u.is_active ? "Desativar" : "Aprovar"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DashboardTokens() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    adminDashboard()
      .then(setData)
      .catch((e) => setErro(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-gray-500">Carregando...</p>;
  if (erro) return <p className="text-sm text-red-500">{erro}</p>;
  if (!data) return null;

  const kpis = [
    { label: "Total de usuários", value: data.total_usuarios },
    { label: "Ativos", value: data.usuarios_ativos },
    { label: "Aguardando aprovação", value: data.usuarios_aguardando },
    { label: "Tokens hoje", value: data.tokens_hoje.toLocaleString("pt-BR") },
    { label: "Tokens 7 dias", value: data.tokens_semana.toLocaleString("pt-BR") },
    { label: "Tokens 30 dias", value: data.tokens_mes.toLocaleString("pt-BR") },
    { label: "Tokens total", value: data.tokens_total.toLocaleString("pt-BR") },
  ];

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div
            key={k.label}
            className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4"
          >
            <p className="text-xs text-gray-500 dark:text-gray-400">{k.label}</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums">
              {k.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Média por tipo de geração
          </h2>
          <dl className="space-y-2 text-sm">
            {[
              ["ETP", data.media_tokens_etp],
              ["TR", data.media_tokens_tr],
              ["Pesquisa", data.media_tokens_pesquisa],
              ["Análise", data.media_tokens_analise],
            ].map(([label, val]) => (
              <div key={String(label)} className="flex justify-between">
                <dt className="text-gray-500 dark:text-gray-400">{label}</dt>
                <dd className="font-medium text-gray-900 dark:text-gray-100 tabular-nums">
                  {Number(val).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Top 10 usuários por consumo
          </h2>
          <ol className="space-y-1 text-sm">
            {data.top_usuarios.map((u, i) => (
              <li key={u.email} className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">
                  <span className="mr-2 text-gray-400">{i + 1}.</span>
                  {u.nome}
                </span>
                <span className="font-medium text-gray-900 dark:text-gray-100 tabular-nums">
                  {u.tokens_total.toLocaleString("pt-BR")}
                </span>
              </li>
            ))}
            {data.top_usuarios.length === 0 && (
              <li className="text-gray-400 text-xs">Nenhum dado ainda</li>
            )}
          </ol>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Tokens por dia (últimos 30 dias)
        </h2>
        {data.tokens_por_dia.length === 0 ? (
          <p className="text-xs text-gray-400">Nenhum dado ainda</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="text-left text-gray-500 font-medium pb-2">Data</th>
                  <th className="text-right text-gray-500 font-medium pb-2">Tokens</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                {data.tokens_por_dia.map((d) => (
                  <tr key={d.data}>
                    <td className="py-1 text-gray-600 dark:text-gray-400">{d.data}</td>
                    <td className="py-1 text-right tabular-nums text-gray-900 dark:text-gray-100">
                      {d.total.toLocaleString("pt-BR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
