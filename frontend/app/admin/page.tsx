"use client";

import { AuthGuard } from "@/components/auth-guard";
import {
  adminAtivar,
  adminDashboard,
  adminDesativar,
  adminListarUsuarios,
  type AdminDashboard,
  type AdminUsuario,
  type EstatsFaseAdmin,
} from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useEffect, useState } from "react";

export default function AdminPage() {
  return (
    <AuthGuard requireOwner>
      <AdminPanel />
    </AuthGuard>
  );
}

function AdminPanel() {
  return (
    <div className="min-h-screen bg-background py-8 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">
              Painel de Administração
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Gerencie usuários e monitore o consumo de tokens
            </p>
          </div>
          <Button variant="outline" size="sm" render={<a href="/" />}>
            Voltar ao sistema
          </Button>
        </div>

        <Tabs defaultValue="usuarios">
          <TabsList variant="line" className="w-full justify-start border-b border-border rounded-none pb-0 h-auto">
            <TabsTrigger value="usuarios" className="px-4 pb-3 rounded-none">
              Usuários
            </TabsTrigger>
            <TabsTrigger value="dashboard" className="px-4 pb-3 rounded-none">
              Dashboard de Tokens
            </TabsTrigger>
          </TabsList>

          <TabsContent value="usuarios" className="mt-6">
            <TabelaUsuarios />
          </TabsContent>

          <TabsContent value="dashboard" className="mt-6">
            <DashboardTokens />
          </TabsContent>
        </Tabs>
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
      .catch((e: unknown) => setErro(e instanceof Error ? e.message : "Erro"))
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

  if (loading) return <p className="text-sm text-muted-foreground py-6">Carregando...</p>;
  if (erro) return <p className="text-sm text-destructive py-6">{erro}</p>;

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nome</TableHead>
            <TableHead>E-mail</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Tokens</TableHead>
            <TableHead>Cadastro</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {usuarios.map((u) => (
            <TableRow key={u.id}>
              <TableCell className="font-medium">
                <span className="text-foreground">{u.nome}</span>
                {u.is_owner && (
                  <Badge variant="outline" className="ml-2 text-[10px]">
                    owner
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">{u.email}</TableCell>
              <TableCell>
                <Badge variant={u.is_active ? "default" : "secondary"}>
                  {u.is_active ? "Ativo" : "Aguardando"}
                </Badge>
              </TableCell>
              <TableCell className="tabular-nums text-muted-foreground">
                {u.tokens_total.toLocaleString("pt-BR")}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {u.criado_em ? new Date(u.criado_em).toLocaleDateString("pt-BR") : "—"}
              </TableCell>
              <TableCell>
                {!u.is_owner && (
                  <Button
                    size="sm"
                    variant={u.is_active ? "destructive" : "default"}
                    className="h-7 px-3 text-xs"
                    onClick={() => toggle(u)}
                  >
                    {u.is_active ? "Desativar" : "Aprovar"}
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function DashboardTokens() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    adminDashboard()
      .then(setData)
      .catch((e: unknown) => setErro(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground py-6">Carregando...</p>;
  if (erro) return <p className="text-sm text-destructive py-6">{erro}</p>;
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
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <Card key={k.label} size="sm">
            <CardContent className="pt-4">
              <p className="text-xs text-muted-foreground">{k.label}</p>
              <p className="mt-1 text-2xl font-bold text-foreground tabular-nums">
                {k.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Média por tipo de geração</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-2 text-sm">
              {(
                [
                  ["ETP", data.media_tokens_etp],
                  ["TR", data.media_tokens_tr],
                  ["Pesquisa", data.media_tokens_pesquisa],
                  ["Análise", data.media_tokens_analise],
                ] as [string, number][]
              ).map(([label, val]) => (
                <div key={label} className="flex justify-between items-center">
                  <dt className="text-muted-foreground">{label}</dt>
                  <dd className="font-medium text-foreground tabular-nums">
                    {Number(val).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}
                  </dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Top 10 por consumo</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-1.5 text-sm">
              {data.top_usuarios.map((u, i) => (
                <li key={u.email} className="flex justify-between items-center">
                  <span className="text-muted-foreground">
                    <span className="mr-2 text-xs text-muted-foreground/60 tabular-nums">
                      {i + 1}.
                    </span>
                    {u.nome}
                  </span>
                  <span className="font-medium text-foreground tabular-nums">
                    {u.tokens_total.toLocaleString("pt-BR")}
                  </span>
                </li>
              ))}
              {data.top_usuarios.length === 0 && (
                <li className="text-xs text-muted-foreground">Nenhum dado ainda</li>
              )}
            </ol>
          </CardContent>
        </Card>
      </div>

      {/* Métricas de Contratações */}
      {(data.stats_perguntas_global?.total_chamadas > 0 ||
        data.stats_bcc_global?.total_chamadas > 0) && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-foreground">Métricas de Contratações (global)</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {(
              [
                ["Geração de Perguntas", data.stats_perguntas_global],
                ["Base de Conhecimento", data.stats_bcc_global],
              ] as [string, EstatsFaseAdmin][]
            ).map(([label, s]) => (
              <Card key={label}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{label}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-x-4 gap-y-2 text-sm">
                    {(
                      [
                        ["Chamadas", s.total_chamadas, 0],
                        ["Média", s.media, 0],
                        ["Mediana", s.mediana, 0],
                        ["Mínimo", s.minimo, 0],
                        ["Máximo", s.maximo, 0],
                        ["Variância", s.variancia, 0],
                      ] as [string, number, number][]
                    ).map(([k, v, d]) => (
                      <div key={k}>
                        <p className="text-[10px] text-muted-foreground">{k}</p>
                        <p className="font-semibold tabular-nums text-xs">
                          {v.toLocaleString("pt-BR", { maximumFractionDigits: d })}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Tokens por dia (últimos 30 dias)</CardTitle>
        </CardHeader>
        <CardContent>
          {data.tokens_por_dia.length === 0 ? (
            <p className="text-xs text-muted-foreground">Nenhum dado ainda</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Data</TableHead>
                  <TableHead className="text-xs text-right">Tokens</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.tokens_por_dia.map((d) => (
                  <TableRow key={d.data}>
                    <TableCell className="text-xs text-muted-foreground">{d.data}</TableCell>
                    <TableCell className="text-xs text-right tabular-nums text-foreground">
                      {d.total.toLocaleString("pt-BR")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
