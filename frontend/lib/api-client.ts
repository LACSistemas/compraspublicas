import type {
  Analise,
  AnaliseCreateResponse,
  Geracao,
  GeracaoCreatePayload,
  GeracaoCreateResponse,
  Pesquisa,
  PesquisaCreatePayload,
  PesquisaDetalhe,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Sessão expirada");
  }

  if (response.status === 403) {
    const body = await response.json().catch(() => ({}));
    const detail: string = body.detail ?? "";
    if (detail.toLowerCase().includes("aguardando")) {
      window.location.href = "/aguardando";
    }
    throw new Error(detail || "Acesso negado");
  }

  if (!response.ok) {
    const corpo = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${corpo}`);
  }

  return response.json() as Promise<T>;
}

export function criarPesquisa(payload: PesquisaCreatePayload): Promise<Pesquisa> {
  return request<Pesquisa>("/pesquisas", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listarPesquisas(): Promise<Pesquisa[]> {
  return request<Pesquisa[]>("/pesquisas");
}

export function getPesquisa(id: number): Promise<PesquisaDetalhe> {
  return request<PesquisaDetalhe>(`/pesquisas/${id}`);
}

export function getPesquisaStatus(id: number): Promise<Pesquisa> {
  return request<Pesquisa>(`/pesquisas/${id}/status`);
}

export function dispararAnalise(id: number): Promise<AnaliseCreateResponse> {
  return request<AnaliseCreateResponse>(`/pesquisas/${id}/analise`, {
    method: "POST",
  });
}

export function getAnalise(id: number): Promise<Analise> {
  return request<Analise>(`/pesquisas/${id}/analise`);
}

export function gerarETP(
  pesquisaId: number,
  payload: GeracaoCreatePayload,
): Promise<GeracaoCreateResponse> {
  return request<GeracaoCreateResponse>(`/pesquisas/${pesquisaId}/etp`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getGeracaoETP(pesquisaId: number, tipo = "etp"): Promise<Geracao> {
  return request<Geracao>(`/pesquisas/${pesquisaId}/etp?tipo=${tipo}`);
}

export function getUrlDownloadETP(pesquisaId: number, tipo = "etp"): string {
  const token = getToken();
  return `${API_URL}/pesquisas/${pesquisaId}/etp/download?tipo=${tipo}${token ? `&token=${token}` : ""}`;
}

// Auth
export async function apiLogin(email: string, password: string): Promise<{ access_token: string }> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status}`);
  }
  return res.json();
}

export async function apiRegister(nome: string, email: string, password: string): Promise<void> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, email, password }),
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status}`);
  }
}

// Admin
export async function adminListarUsuarios() {
  return request<AdminUsuario[]>("/admin/usuarios");
}

export async function adminAtivar(id: number) {
  return request<AdminUsuario>(`/admin/usuarios/${id}/ativar`, { method: "PATCH" });
}

export async function adminDesativar(id: number) {
  return request<AdminUsuario>(`/admin/usuarios/${id}/desativar`, { method: "PATCH" });
}

export async function adminDashboard() {
  return request<AdminDashboard>("/admin/dashboard");
}

export interface AdminUsuario {
  id: number;
  email: string;
  nome: string;
  is_active: boolean;
  is_owner: boolean;
  tokens_total: number;
  criado_em: string | null;
}

export interface AdminDashboard {
  total_usuarios: number;
  usuarios_ativos: number;
  usuarios_aguardando: number;
  tokens_hoje: number;
  tokens_semana: number;
  tokens_mes: number;
  tokens_total: number;
  media_tokens_etp: number;
  media_tokens_tr: number;
  media_tokens_pesquisa: number;
  media_tokens_analise: number;
  tokens_por_dia: { data: string; total: number }[];
  tokens_por_tipo: { tipo: string; total: number; media: number }[];
  top_usuarios: { email: string; nome: string; tokens_total: number }[];
}
