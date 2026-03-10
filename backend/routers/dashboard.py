from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models, schemas

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
def obter_estatisticas(db: Session = Depends(get_db)):
    total_tipos = db.query(func.count(models.ItemType.id)).scalar() or 0

    total_comprado = db.query(func.sum(models.Purchase.quantidade)).scalar() or 0

    entradas = db.query(func.sum(models.StockMovement.quantidade)).filter(
        models.StockMovement.tipo.in_(["entrada", "ajuste"])
    ).scalar() or 0
    saidas = db.query(func.sum(models.StockMovement.quantidade)).filter(
        models.StockMovement.tipo.in_(["saida", "perda", "descarte"])
    ).scalar() or 0
    total_estoque = max(0, entradas - saidas)

    total_lavanderia = db.query(
        func.sum(models.LaundryRecord.quantidade_enviada - models.LaundryRecord.quantidade_retornada)
    ).filter(
        models.LaundryRecord.status.in_(["pendente", "parcial"])
    ).scalar() or 0
    total_lavanderia = max(0, total_lavanderia)

    total_em_uso = db.query(func.sum(models.RoomAssignment.quantidade)).filter(
        models.RoomAssignment.ativo == 1
    ).scalar() or 0

    total_contabilizado = total_estoque + total_lavanderia + total_em_uso
    total_desfalque = max(0, total_comprado - total_contabilizado)
    percentual = round((total_desfalque / total_comprado * 100) if total_comprado > 0 else 0, 1)

    alertas = []
    if percentual > 10:
        alertas.append(f"⚠️ ALERTA CRÍTICO: Desfalque de {percentual}% detectado!")
    elif percentual > 5:
        alertas.append(f"🟠 Atenção: Desfalque de {percentual}% acima do ideal")
    elif percentual > 2:
        alertas.append(f"🟡 Desfalque de {percentual}% — monitorar")

    pendentes_lavanderia = db.query(func.count(models.LaundryRecord.id)).filter(
        models.LaundryRecord.status.in_(["pendente", "parcial"])
    ).scalar() or 0
    if pendentes_lavanderia > 0:
        alertas.append(f"🧺 {pendentes_lavanderia} lote(s) aguardando retorno da lavanderia")

    ultimas_auditorias = db.query(models.AuditReport).order_by(
        models.AuditReport.created_at.desc()
    ).limit(5).all()

    return schemas.DashboardStats(
        total_tipos_item=total_tipos,
        total_comprado=total_comprado,
        total_estoque=total_estoque,
        total_na_lavanderia=total_lavanderia,
        total_em_uso=total_em_uso,
        total_desfalque=total_desfalque,
        percentual_desfalque=percentual,
        alertas=alertas,
        ultimas_auditorias=ultimas_auditorias
    )
