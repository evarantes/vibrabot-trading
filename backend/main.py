from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CodexiaAuditor",
    description="Sistema de Auditoria de Enxoval Hoteleiro com IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import items, purchases, stock, laundry, rooms, audit, dashboard

app.include_router(items.router)
app.include_router(purchases.router)
app.include_router(stock.router)
app.include_router(laundry.router)
app.include_router(rooms.router)
app.include_router(audit.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "app": "CodexiaAuditor",
        "versao": "1.0.0",
        "descricao": "Sistema de Auditoria de Enxoval Hoteleiro com IA",
        "docs": "/docs"
    }


@app.get("/health", tags=["Root"])
def health():
    return {"status": "ok"}
