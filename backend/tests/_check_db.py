from app.database import Base, engine
from app import models  # noqa: F401  (registra Pesquisa/Analise em Base.metadata)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso em", engine.url)
