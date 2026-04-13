# templates_ia.py
'''
Por enquanto, este resumo está pre definido para não perder tempo do MVP
No futuro, a IA que vai fazer estes resumos e salvar em um arquivo específico
Para criar esta IA, devemos fazer no repositóiro Modulo5 Analise Codigo (Para pegar todas as informações de acordo com o usuário - Tech Lead, Dev ou PM)
Por fim, após juntar esta análise, o Modulo5 Gerador Documentacao vai usar esta análise para fazer uma documentação visual
'''

resumo_tech_lead = """
[SIMULAÇÃO IA - VISÃO DE ARQUITETURA]
FOCO: Infraestrutura e Dependências
-------------------------------------------
1. Cloud Service (Azure App Service)
2. Database (PostgreSQL)
3. Cache System (Redis)
-------------------------------------------
Status: Pronto para provisionamento via Terraform.
"""

resumo_desenvolvedor = """
[SIMULAÇÃO IA - FLUXO DE LÓGICA]
FOCO: Algoritmos e Implementação
-------------------------------------------
- main.py -> chama selecionar_perfil()
- usuarios.py -> instanciam classes herdadas
- fluxo -> tratamento de erros de input
-------------------------------------------
Status: Cobertura de testes em 100%.
"""

resumo_product_manager = """
[SIMULAÇÃO IA - VISÃO DE NEGÓCIO]
FOCO: Roadmap e Entrega de Valor
-------------------------------------------
- Feature: Gerenciamento de Personas
- Prazo: Entrega MVP P5 (12/04)
- Valor: Redução de 40% no tempo de documentação.
-------------------------------------------
Status: Alinhado com as metas da Sprint.
"""