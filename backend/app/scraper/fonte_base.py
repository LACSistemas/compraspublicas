from abc import ABC, abstractmethod


class FonteDados(ABC):
    @abstractmethod
    def buscar(self, termo: str, limite: int) -> list:
        """Busca processos pelo termo e retorna até `limite` itens da lista."""

    @abstractmethod
    def detalhar(self, lista_item: dict) -> dict:
        """Retorna o detalhe completo de um processo dado o item da lista."""

    @abstractmethod
    def listar_itens(self, codigo_licitacao: int) -> dict:
        """Retorna a estrutura de itens/lotes do processo."""

    @abstractmethod
    def listar_documentos(self, codigo_licitacao: int) -> list:
        """Retorna a lista de documentos disponíveis para download."""

    @abstractmethod
    def baixar_documento(self, doc: dict, destino: str) -> int:
        """Baixa o arquivo do documento para `destino`. Retorna bytes gravados."""
