import type {
  Analise,
  AnaliseCreateResponse,
  Pesquisa,
  PesquisaCreatePayload,
  PesquisaDetalhe,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

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
