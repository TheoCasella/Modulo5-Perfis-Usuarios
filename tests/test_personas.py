from src.models.usuarios import TechLead

# Testar a criação do tech lead
def test_criacao_tech_lead():
    lider = TechLead("Carlos")
    assert lider.cargo == "Tech Lead" # assert --> "Garanta que..."
    assert "Arquitetura de Nuvem" in lider.interesses_principais
    print("\nTeste de criação de Tech Lead: PASSOU")

if __name__ == "__main__":
    test_criacao_tech_lead()