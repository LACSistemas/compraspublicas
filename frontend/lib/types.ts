export type StatusPesquisa = "pendente" | "em_andamento" | "completo" | "erro";

export interface Documento {
  nome?: string;
  tipo?: string;
  data?: string;
}

export interface Item {
  numero?: string;
  descricao?: string;
  quantidade?: string;
  unidade?: string;
  disputa?: string;
  situacao_item?: string;
  melhor_lance?: string;
  [chave: string]: string | undefined;
}

export interface Andamento {
  data_hora_autor?: string;
  descricao?: string;
}

export interface ArquivoBaixado {
  arquivo: string;
  tamanho_bytes: number;
  pasta: string;
}

export interface Processo {
  url: string;
  numero_processo?: string;
  situacao?: string;
  comprador?: string;
  modalidade?: string;
  objeto?: string;
  informacoes?: Record<string, string>;
  datas?: Record<string, string>;
  documentos?: Documento[];
  itens?: Item[];
  andamento?: Andamento[];
  conteudo_bruto?: string[];
  arquivos_baixados?: ArquivoBaixado[];
}

export interface ResultadoScraping {
  termo_busca: string;
  processos: Processo[];
  erro: string | null;
}

export interface Pesquisa {
  id: number;
  termo_busca: string;
  quantidade_desejada: string | null;
  status: StatusPesquisa;
  erro_mensagem?: string | null;
  criado_em: string;
}

export interface PesquisaDetalhe extends Pesquisa {
  limite_processos: number;
  resultado: ResultadoScraping | null;
  pasta_downloads: string | null;
  atualizado_em: string;
}

export type StatusAnalise = "pendente" | "em_andamento" | "completo" | "erro";

export interface Metadados {
  orgao?: string;
  secretaria?: string;
  municipio_uf?: string;
  numero_processo?: string;
  modalidade?: string;
  criterio_julgamento?: string;
  situacao?: string;
  objeto?: string;
  natureza_objeto?: string;
  valor_estimado?: string;
  data_publicacao?: string;
  data_abertura?: string;
}

export interface DocumentoAuditado {
  nome: string;
  tipo_detectado?: string;
  tipo_informado_portal?: string;
  data?: string;
  versao_vigente?: boolean;
  observacoes?: string;
}

export interface ItemAuditado {
  numero?: string;
  descricao?: string;
  quantidade?: string;
  unidade?: string;
  valor_unitario?: string;
  valor_total?: string;
}

export type Classificacao = "C" | "PC" | "NC" | "N/A";

export interface ClassificacaoChecklist {
  item: string;
  descricao?: string;
  classificacao: Classificacao;
  justificativa?: string;
  gera_constatacao?: boolean;
}

export type GrauRisco = "Baixo" | "Médio" | "Alto" | "Crítico";

export interface Constatacao {
  numero?: string;
  classificacao: "PC" | "NC";
  risco: GrauRisco;
  descricao_sumaria: string;
  situacao_encontrada: string;
  recomendacao: string;
  documentos_base?: string[];
}

export interface QuadroSintese {
  total_itens: number;
  conformes: number;
  parcialmente_conformes: number;
  nao_conformes: number;
  na: number;
  percentual_conformidade: string;
  grau_risco_geral: GrauRisco;
}

// Relatório de auditoria de 1 processo (schema da seção 20 do prompt.md)
export interface ProcessoAuditado {
  url?: string;
  metadados: Metadados;
  documentos_auditados: DocumentoAuditado[];
  documentos_ausentes: string[];
  itens: ItemAuditado[];
  classificacao_checklist: ClassificacaoChecklist[];
  constatacoes: Constatacao[];
  dicas_aprimoramento: string[];
  recomendacoes_consolidadas: string[];
  quadro_sintese: QuadroSintese;
}

export interface AnaliseResultado {
  processos_auditados: ProcessoAuditado[];
}

export interface Analise {
  id: number;
  status: StatusAnalise;
  erro_mensagem?: string | null;
  resultado: AnaliseResultado | null;
  modelo_gemini?: string | null;
}

export interface PesquisaCreatePayload {
  termo_busca: string;
  quantidade_desejada?: string | null;
}

export interface AnaliseCreateResponse {
  analise_id: number;
  status: string;
}
