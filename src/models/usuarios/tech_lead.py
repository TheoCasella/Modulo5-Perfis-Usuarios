from src.models.usuarios.usuarios import PersonaTecnica
from src.models.usuarios.usuarios import resumo_tech_lead

# Ficha específica para Tech Lead
class TechLead(PersonaTecnica):
    def __init__(self, nome):
        super().__init__(
            nome = nome,
            cargo = "Tech Lead",
            interesses_principais = ["Diagramas de Sequência", "Arquitetura de Nuvem", "Acoplamento de Módulos"]
        )
    #Serve para a IA "entender" qual usuário é
    def get_foco_ia(self):
        return resumo_tech_lead