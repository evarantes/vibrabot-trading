from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import json
from database import get_db
import models, schemas
from services.ai_service import calcular_auditoria, gerar_analise_ia

router = APIRouter(prefix="/audit", tags=["Auditoria"])


def _coletar_dados_auditoria(db: Session, periodo_inicio=None, periodo_fim=None) -> dict:
    """Coleta todos os dados necessários para a auditoria."""
    itens = db.query(models.ItemType).all()
    dados_itens = []

    for item in itens:
        # Total comprado
        query_compra = db.query(func.sum(models.Purchase.quantidade)).filter(
            models.Purchase.item_type_id == item.id
        )
        if periodo_inicio:
            query_compra = query_compra.filter(models.Purchase.data_compra >= periodo_inicio)
        if periodo_fim:
            query_compra = query_compra.filter(models.Purchase.data_compra <= periodo_fim)
        total_comprado = query_compra.scalar() or 0

        # Saldo em estoque (entradas - saídas de movimentos)
        entradas = db.query(func.sum(models.StockMovement.quantidade)).filter(
            models.StockMovement.item_type_id == item.id,
            models.StockMovement.tipo.in_(["entrada", "ajuste"])
        ).scalar() or 0

        saidas = db.query(func.sum(models.StockMovement.quantidade)).filter(
            models.StockMovement.item_type_id == item.id,
            models.StockMovement.tipo.in_(["saida", "perda", "descarte"])
        ).scalar() or 0

        saldo_estoque = max(0, entradas - saidas)

        # Total na lavanderia (pendente ou parcial)
        na_lavanderia = db.query(
            func.sum(models.LaundryRecord.quantidade_enviada - models.LaundryRecord.quantidade_retornada)
        ).filter(
            models.LaundryRecord.item_type_id == item.id,
            models.LaundryRecord.status.in_(["pendente", "parcial"])
        ).scalar() or 0
        na_lavanderia = max(0, na_lavanderia)

        # Total em uso nos quartos
        em_uso = db.query(func.sum(models.RoomAssignment.quantidade)).filter(
            models.RoomAssignment.item_type_id == item.id,
            models.RoomAssignment.ativo == 1
        ).scalar() or 0

        if total_comprado > 0 or saldo_estoque > 0 or na_lavanderia > 0 or em_uso > 0:
            dados_itens.append({
                "item_type_id": item.id,
                "item_nome": item.nome,
                "categoria": item.categoria,
                "total_comprado": total_comprado,
                "saldo_estoque": saldo_estoque,
                "na_lavanderia": na_lavanderia,
                "em_uso": em_uso
            })

    periodo = "Geral"
    if periodo_inicio and periodo_fim:
        periodo = f"{periodo_inicio.strftime('%d/%m/%Y')} a {periodo_fim.strftime('%d/%m/%Y')}"
    elif periodo_inicio:
        periodo = f"A partir de {periodo_inicio.strftime('%d/%m/%Y')}"
    elif periodo_fim:
        periodo = f"Até {periodo_fim.strftime('%d/%m/%Y')}"

    return {"itens": dados_itens, "periodo": periodo}


@router.post("/gerar", response_model=schemas.AuditReportOut, status_code=201)
def gerar_auditoria(request: schemas.AuditRequest, db: Session = Depends(get_db)):
    dados = _coletar_dados_auditoria(db, request.periodo_inicio, request.periodo_fim)

    if not dados["itens"]:
        raise HTTPException(
            status_code=400,
            detail="Nenhum dado encontrado para gerar auditoria. Registre compras e movimentações primeiro."
        )

    resultado = calcular_auditoria(dados)
    analise = gerar_analise_ia(dados, resultado)

    totais = resultado["totais"]
    relatorio_completo = {
        "dados_entrada": dados,
        "resultado": resultado,
        "gerado_em": datetime.now().isoformat()
    }

    db_auditoria = models.AuditReport(
        titulo=request.titulo,
        periodo_inicio=request.periodo_inicio,
        periodo_fim=request.periodo_fim,
        relatorio_json=json.dumps(relatorio_completo, ensure_ascii=False),
        analise_ia=analise,
        total_comprado=totais["total_comprado"],
        total_estoque=totais["total_estoque"],
        total_lavanderia=totais["total_na_lavanderia"],
        total_em_uso=totais["total_em_uso"],
        total_desfalque=totais["total_desfalque"]
    )

    db.add(db_auditoria)
    db.commit()
    db.refresh(db_auditoria)
    return db_auditoria


@router.get("/", response_model=List[schemas.AuditReportOut])
def listar_auditorias(db: Session = Depends(get_db)):
    return db.query(models.AuditReport).order_by(
        models.AuditReport.created_at.desc()
    ).all()


@router.get("/preview")
def preview_auditoria(
    periodo_inicio: Optional[datetime] = None,
    periodo_fim: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Mostra os dados que serão usados na auditoria sem salvar."""
    dados = _coletar_dados_auditoria(db, periodo_inicio, periodo_fim)
    resultado = calcular_auditoria(dados)
    return resultado


@router.get("/{auditoria_id}", response_model=schemas.AuditReportOut)
def obter_auditoria(auditoria_id: int, db: Session = Depends(get_db)):
    auditoria = db.query(models.AuditReport).filter(
        models.AuditReport.id == auditoria_id
    ).first()
    if not auditoria:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    return auditoria


@router.delete("/{auditoria_id}", status_code=204)
def deletar_auditoria(auditoria_id: int, db: Session = Depends(get_db)):
    auditoria = db.query(models.AuditReport).filter(
        models.AuditReport.id == auditoria_id
    ).first()
    if not auditoria:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    db.delete(auditoria)
    db.commit()
