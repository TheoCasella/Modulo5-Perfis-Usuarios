import uvicorn
from fastapi import FastAPI

from app.adapters.driving.http import auditoria_routes, saude_routes


app = FastAPI(
    title="Perfis de Usuarios",
    description="Servico de papeis, ownership, aprovacoes, auditoria e notificacoes do Modulo 5.",
    version="1.0.0",
)

app.include_router(saude_routes.router)
app.include_router(auditoria_routes.router)


@app.get("/")
def read_root():
    return {"message": "Servico de Perfis de Usuarios ativo"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5002, reload=True)
