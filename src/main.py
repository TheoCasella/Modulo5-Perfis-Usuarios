import json
import os
from src.models.usuarios.tech_lead import TechLead
from src.models.usuarios.desenvolvedor import Desenvolvedor
from src.models.usuarios.product_manager import ProductManager

def selecionar_perfil():
    nome = input("\nQual o seu nome? ")
    cargo = input("\nQual seu cargo? (Tech Lead, Desenvolvedor, Product Manager) ")

    if cargo == "Tech Lead":
        return TechLead(nome)
    elif cargo == "Desenvolvedor":
        return Desenvolvedor(nome)
    elif cargo == "Product Manager":
        return ProductManager(nome)
    else:
        return "Erro, cargo inválido"


def exportar_perfil(usuario):
    """Gera o arquivo que será lido pelo módulo de IA"""

    if not os.path.exists("./data"):
        os.makedirs("./data")
        print("[SISTEMA] Pasta 'data' criada com sucesso!")
    caminho_arquivo = "data/contrato_perfil.json"

    contrato = {
        "usuario_nome": usuario.nome,
        "usuario_cargo": usuario.cargo,
        "diretriz_ia": usuario.get_foco_ia()
    }

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(contrato, f, indent=4, ensure_ascii=False)
    print("\n[CONTRATO GERADO] O arquivo 'contrato_perfil.json' está pronto para o Módulo de IA.")


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

        # GERA O CONTRATO (A conexão entre os repositórios)
        exportar_perfil(usuario)