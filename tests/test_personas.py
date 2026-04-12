from src.models.usuarios import TechLead, Desenvolvedor, ProductManager


# Testar a criação do tech lead
def test_criacao_tech_lead():
    lider = TechLead("Carlos")
    assert lider.cargo == "Tech Lead" # assert --> "Garanta que..."
    assert "Arquitetura de Nuvem" in lider.interesses_principais
    print("\nTeste de criação de Tech Lead: PASSOU")

if __name__ == "__main__":
    test_criacao_tech_lead()

def test_criacao_desenvolvedor():
    lider = Desenvolvedor("Ana")
    assert lider.cargo == "Desenvolvedor"
    assert "Lógica de Código" in lider.interesses_principais
    print("\nTeste de criação de Desenvolvedor: PASSOU")

if __name__ == "__main__":
    test_criacao_desenvolvedor()

def test_criacao_product_manager():
    lider = ProductManager("Artur")
    assert lider.cargo == "Product Manager (PM)"
    assert "Valor de Negócio" in lider.interesses_principais
    print("\nTeste de criação de PM: PASSOU")

if __name__ == "__main__":
    test_criacao_product_manager()