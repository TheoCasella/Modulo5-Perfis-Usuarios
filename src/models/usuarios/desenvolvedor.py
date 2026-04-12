from src.models.usuarios.usuarios import PersonaTecnica
from src.models.usuarios.usuarios import resumo_desenvolvedor

# Ficha específica para Desenvolvedor
class Desenvolvedor(PersonaTecnica):
    def __init__(self, nome):
        super().__init__(
            nome = nome,
            cargo = "Desenvolvedor",
            interesses_principais= ["Lógica de Código", "Fluxo de Funcionamento"]
        )

    def get_foco_ia(self):
        return resumo_desenvolvedor