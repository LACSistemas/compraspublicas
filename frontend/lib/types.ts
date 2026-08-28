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

export type StatusGeracao = "pendente" | "em_andamento" | "completo" | "erro";

export interface Geracao {
  id: number;
  tipo: string;
  status: StatusGeracao;
  erro_mensagem?: string | null;
  pendencias?: string[] | null;
  arquivo_disponivel: boolean;
  resultado?: Record<string, unknown> | null;
  modelo_gemini?: string | null;
  criado_em: string;
  atualizado_em: string;
}

export interface GeracaoCreatePayload {
  tipo: "dfd" | "etp" | "mapa_riscos" | "tr";
  un_gestora: string;
  responsaveis: string;
  objeto_resumido?: string | null;
}

export interface GeracaoCreateResponse {
  geracao_id: number;
  status: string;
}

// ── Contratações ──────────────────────────────────────────────────────────────

export type StatusContratacao =
  | "cadastro"
  | "gerando_plano"
  | "gerando_perguntas"
  | "investigacao"
  | "processando_bcc"
  | "bcc_ativa"
  | "erro";

export interface Alternativa {
  letra: string;
  texto: string;
}

export interface PerguntaContratacao {
  id: number;
  ordem: number;
  texto: string;
  alternativas: Alternativa[];
  resposta_escolhida: string | null;
  respondida_em: string | null;
}

export interface EvidenciaBCC {
  id: string;
  descricao: string;
  origem: string;
  data_coleta: string;
  responsavel: string;
  confiabilidade: "alta" | "média" | "baixa";
  decisao_relacionada: string;
  status_validacao: "validada" | "pendente" | "frágil" | "contraditória";
  fonte: "ia" | "usuario";
  documentos_impactados: string[];
}

export interface DecisaoBCC {
  id: string;
  pergunta_decisoria: string;
  conclusao: string;
  motivacao_administrativa: string;
  base_legal: string;
  evidencias_utilizadas: string[];
  nivel_robustez_pct: number;
  nivel_robustez_label: string;
  documentos_impactados: string[];
  status: string;
}

export interface LacunaBCC {
  id: string;
  descricao: string;
  criticidade: "alta" | "média" | "baixa";
  responsavel: string;
  decisao_bloqueada: string;
  documentos_bloqueados: string[];
  acao_necessaria: string;
}

export interface RiscoBCC {
  id: string;
  categoria: string;
  descricao: string;
  causa: string;
  consequencia: string;
  probabilidade: "baixa" | "média" | "alta";
  impacto: "baixo" | "médio" | "alto";
  nivel_risco: "baixo" | "médio" | "alto" | "crítico";
  acao_preventiva: string;
  plano_contingencia: string;
  responsavel: string;
  status: string;
  fonte: "ia" | "usuario";
  documentos_impactados: string[];
}

export interface RecomendacaoBCC {
  id: string;
  descricao: string;
  motivo: string;
  prioridade: "alta" | "média" | "baixa";
  beneficio_esperado: string;
  risco_reduzido: string;
  documentos_impactados: string[];
  status: "pendente" | "executada" | "dispensada";
}

export interface DocumentoStatusBCC {
  situacao: string;
  completude_pct: number;
  pendencias: number;
}

export interface FundamentacaoBCC {
  id: string;
  pergunta_decisoria: string;
  conclusao: string;
  justificativa_administrativa: string;
  evidencias_utilizadas: string[];
  base_normativa: string[];
  nivel_robustez_pct: number;
  nivel_robustez_label: string;
  ressalvas: string | null;
}

export interface MetricasBCC {
  progresso_pct: number;
  nivel_maturidade: "Insuficiente" | "Parcial" | "Maduro";
  evidencias_coletadas: number;
  evidencias_total: number;
  decisoes_fundamentadas: number;
  decisoes_total: number;
  pendencias_criticas: number;
}

export interface DadosBCC {
  metricas: MetricasBCC;
  resumo_executivo: {
    necessidade: string;
    solucao_escolhida: string;
    riscos_principais: string[];
  };
  evidencias: EvidenciaBCC[];
  decisoes: DecisaoBCC[];
  lacunas: LacunaBCC[];
  riscos: RiscoBCC[];
  recomendacoes: RecomendacaoBCC[];
  documentos_status: Record<string, DocumentoStatusBCC>;
  fundamentacoes: FundamentacaoBCC[];
  historico: Array<{
    timestamp: string;
    usuario: string;
    acao: string;
    detalhe: string;
  }>;
}

export interface BaseConhecimento {
  progresso_pct: number;
  nivel_maturidade: string;
  dados: DadosBCC;
  atualizado_em: string | null;
}

export interface Contratacao {
  id: number;
  objeto: string;
  orgao_unidade: string;
  numero_processo: string | null;
  equipe_responsavel: string | null;
  tipo_contratacao: string | null;
  contexto_inicial: string | null;
  status: StatusContratacao;
  erro_mensagem: string | null;
  criado_em: string;
  atualizado_em: string;
  perguntas: PerguntaContratacao[];
  base_conhecimento: BaseConhecimento | null;
}

export interface ConsultaPesquisaPrecos {
  id: number;
  ordem: number;
  termo: string;
  status: string;
  processos_encontrados: number;
  processos_novos: number;
}

export interface ObservacaoPreco {
  id: number;
  processo_url: string;
  numero_processo: string | null;
  comprador: string | null;
  descricao_item: string;
  quantidade: string | null;
  unidade: string | null;
  valor_unitario: string;
  tipo_valor: string;
  aderencia_pct: number;
  comparavel: boolean;
  motivo_exclusao: string | null;
  documento_origem: string | null;
  status_validacao: string;
}

export interface CampanhaPesquisaPrecos {
  id: number;
  contratacao_id: number;
  status: "planejada" | "executando" | "pronta_revisao" | "aprovada" | "erro";
  objeto_canonico: { descricao: string; termos_essenciais: string[] };
  max_consultas: number;
  resultado: Record<string, number | string | string[] | number[]>;
  erro_mensagem: string | null;
  aprovado_em: string | null;
  consultas: ConsultaPesquisaPrecos[];
  observacoes: ObservacaoPreco[];
}

export interface PlanoInformacaoView {
  id: number | null;
  codigo: string;
  nome: string;
  tipo: string;
  obrigatoriedade: string;
  estrategia_preferencial: string;
  estrategia: string;
  status: string;
  justificativa_estrategia: string | null;
  valor: unknown;
  origem: string | null;
  confianca: string | null;
  estado_semantico: "nao_informado" | "nao_aplicavel" | "informado" | "inferido" | "confirmado" | "contraditorio";
}

export interface PlanoCardView {
  id: number;
  codigo: string;
  nome: string;
  pergunta_controle: string;
  ordem: number;
  status: string;
  aplicavel: boolean;
  justificativa_dispensa: string | null;
  robustez_pct: number;
  informacoes: PlanoInformacaoView[];
  dependencias: string[];
  dispensa_status: string | null;
  dispensa_revisada_em: string | null;
}

export interface PlanoInvestigacao {
  id: number;
  contratacao_id: number;
  versao: number;
  status: string;
  cards: PlanoCardView[];
  criado_em: string;
  atualizado_em: string;
}

export interface LacunaPlano {
  plano_informacao_id: number;
  plano_card_id: number;
  codigo_card: string;
  codigo_informacao: string;
  nome_informacao: string;
  estrategia: string;
  prioridade: number;
  status: string;
  obrigatoria: boolean;
  bloqueia_conhecimento: boolean;
}

export interface ResumoLacunasPlano {
  plano_id: number;
  total: number;
  bloqueantes: number;
  opcionais: number;
  pronto_para_conhecimento: boolean;
  proxima_estrategia: string | null;
  lacunas: LacunaPlano[];
}

export interface EvidenciaPlano {
  id: number;
  plano_informacao_id: number;
  tipo: string;
  descricao: string;
  conteudo: unknown;
  origem: string;
  metodo_obtencao: string;
  confianca: string;
  hash_conteudo: string;
  status_validacao: string;
  estado: string;
  substitui_evidencia_id: number | null;
  criterios_atendidos: string[];
  criado_em: string;
}

export interface ConhecimentoCard {
  id: number;
  plano_card_id: number;
  codigo_card: string;
  versao: number;
  conclusao: string;
  motivacao: string;
  fundamentacao: string[];
  riscos: unknown[];
  recomendacoes: unknown[];
  evidencias: number[];
  robustez_pct: number;
  status: string;
  aprovado_em: string | null;
  cobertura_criterios: Array<{ codigo: string; descricao: string; atendido: boolean }>;
  dimensoes_robustez: Record<string, number>;
  fontes_confirmadas: Array<{ codigo: string; titulo: string; referencia: string; dispositivo: string; url_oficial: string; orgao_emissor: string }>;
}

// ── Estatísticas de tokens ────────────────────────────────────────────────────

export interface EstatsFase {
  total_chamadas: number;
  media: number;
  mediana: number;
  variancia: number;
  minimo: number;
  maximo: number;
}

export interface TokensPorContratacao {
  contratacao_id: number;
  objeto: string;
  tokens_perguntas_input: number;
  tokens_perguntas_output: number;
  tokens_perguntas_total: number;
  tokens_bcc_input: number;
  tokens_bcc_output: number;
  tokens_bcc_total: number;
  total: number;
}

export interface EstatisticasTokensOut {
  perguntas: EstatsFase;
  bcc: EstatsFase;
  por_contratacao: TokensPorContratacao[];
}
