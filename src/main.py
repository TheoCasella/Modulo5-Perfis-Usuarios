from src.models.usuarios.tech_lead import TechLead
from src.models.usuarios.desenvolvedor import Desenvolvedor
from src.models.usuarios.product_manager import ProductManager

def selecionar_perfil():
    nome = input("\nQual o seu nome? ")
    cargo = input("\nQual seu cargo? ")

    if cargo == "TechLead":
        return TechLead(nome)
    elif cargo == "Desenvolvedor":
        return Desenvolvedor(nome)
    elif cargo == "ProductManager":
        return ProductManager(nome)
    else:
        return "Erro, cargo inválido"

if __name__ == "__main__":
    usuario = selecionar_perfil()
    if isinstance(usuario, str):
        print(usuario)
    else:
        print("\n*** MVP Perfis de Usuários ***")
        print(f"Usuário: {usuario.nome}")
        print(f"Cargo: {usuario.cargo}")
        print(f"Interesses: {', '.join(usuario.interesses_principais)}")
        print(f"Ação da IA: {usuario.get_foco_ia()}")