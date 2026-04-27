# Ponto de entrada da aplicação
# Responsabilidade: instanciar a app e iniciar o servidor.

from app.config.composition_root import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5002) # Porta 5002 pra não colidir com os outros serviços (Interface-e-Nuvem provavelmente em 5000, IA em 5001...)