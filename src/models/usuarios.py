#Define as regras de como um usuário vai ser reconhecido pelo sistema

# Ficha cadastral básica
class PersonaTecnica:
    def __init__(self, nome, cargo, interesses_principais):
        self.nome = nome
        self.cargo = cargo
        self.interesses_principais = interesses_principais

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
        return "Gerar visões de alto nível e dependências de infraestrutura"

# Ficha específica para Desenvolvedor
class Desenvolvedor(PersonaTecnica):
    def __init__(self, nome):
        super().__init__(
            nome = nome,
            cargo = "Desenvolvedor",
            interesses_principais= ["Lógica de Código", "Fluxo de Funcionamento"]
        )

    def get_foco_ia(self):
        return "Gerar visões de lógica de código e fluxo de funcionamento"