from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.adapters.driving.http import (
    aprovacao_routes,
    auditoria_routes,
    notificacao_routes,
    ownership_routes,
    saude_routes,
    sugestao_ownership_routes,
    template_aprovacao_routes,
)
from app.config.composition_root import get_root


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Liga jobs em background no startup (PU-02 scheduler diario).
    root = get_root()
    root.iniciar_jobs_em_background()
    try:
        yield
    finally:
        root.parar_jobs_em_background()


app = FastAPI(
    title="Perfis de Usuarios",
    description="Servico de papeis, ownership, aprovacoes, auditoria e notificacoes do Modulo 5.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(saude_routes.router)
app.include_router(auditoria_routes.router)
app.include_router(ownership_routes.router)
app.include_router(template_aprovacao_routes.router)
app.include_router(aprovacao_routes.router)
app.include_router(notificacao_routes.router)
app.include_router(sugestao_ownership_routes.router)


@app.get("/")
def read_root():
    return {"message": "Servico de Perfis de Usuarios ativo"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5002, reload=True)
