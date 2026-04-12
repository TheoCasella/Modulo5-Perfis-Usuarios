#Define as regras de como um usuário vai ser reconhecido pelo sistema
from src.models.resumos_ia import resumo_tech_lead, resumo_desenvolvedor, resumo_product_manager


# Ficha cadastral básica
class PersonaTecnica:
    def __init__(self, nome, cargo, interesses_principais):
        self.nome = nome
        self.cargo = cargo
        self.interesses_principais = interesses_principais
