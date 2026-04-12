from src.models.usuarios import TechLead
from src.models.usuarios import Desenvolvedor
from src.models.usuarios import ProductManager

def selecionar_perfil():
    nome = input("Qual o seu nome?")
    cargo = input("\nQual seu cargo?")

    if cargo == "TechLead":
        return TechLead(nome)
    elif cargo == "Desenvolvedor":
        return Desenvolvedor(nome)
    elif cargo == "ProductManager":
        return ProductManager(nome)
    else:
        return "Erro, cargo inválido"