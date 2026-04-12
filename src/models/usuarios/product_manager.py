from src.models.usuarios.usuarios import PersonaTecnica
from src.models.usuarios.usuarios import resumo_product_manager

# Ficha específica para Product Manager (PM)
class ProductManager(PersonaTecnica):
    def __init__(self, nome):
        super().__init__(
            nome = nome,
            cargo = "Product Manager (PM)",
            interesses_principais= ["Roadmap do Produto", "Valor de Negócio", "Métricas de Sucesso", "Status da Sprint"]
        )

    def get_foco_ia(self):
        return resumo_product_manager