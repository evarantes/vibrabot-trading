from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from database import get_db
import models, schemas

router = APIRouter(prefix="/stock", tags=["Estoque"])


@router.get("/", response_model=List[schemas.StockMovementOut])
def listar_movimentos(
    item_type_id: Optional[int] = None,
    tipo: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.StockMovement).options(joinedload(models.StockMovement.item_type))
    if item_type_id:
        query = query.filter(models.StockMovement.item_type_id == item_type_id)
    if tipo:
        query = query.filter(models.StockMovement.tipo == tipo)
    if data_inicio:
        query = query.filter(models.StockMovement.data_movimento >= data_inicio)
    if data_fim:
        query = query.filter(models.StockMovement.data_movimento <= data_fim)
    return query.order_by(models.StockMovement.data_movimento.desc()).all()


@router.post("/", response_model=schemas.StockMovementOut, status_code=201)
def criar_movimento(movimento: schemas.StockMovementCreate, db: Session = Depends(get_db)):
    item = db.query(models.ItemType).filter(models.ItemType.id == movimento.item_type_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tipo de item não encontrado")
    if movimento.tipo not in ["entrada", "saida", "ajuste", "perda", "descarte"]:
        raise HTTPException(status_code=400, detail="Tipo deve ser: entrada, saida, ajuste, perda ou descarte")
    db_movimento = models.StockMovement(**movimento.model_dump())
    db.add(db_movimento)
    db.commit()
    db.refresh(db_movimento)
    return db_movimento


@router.get("/summary", response_model=List[schemas.StockSummary])
def resumo_estoque(db: Session = Depends(get_db)):
    itens = db.query(models.ItemType).all()
    resultado = []
    for item in itens:
        total_comprado = db.query(func.sum(models.Purchase.quantidade)).filter(
            models.Purchase.item_type_id == item.id
        ).scalar() or 0

        entradas = db.query(func.sum(models.StockMovement.quantidade)).filter(
            models.StockMovement.item_type_id == item.id,
            models.StockMovement.tipo.in_(["entrada", "ajuste"])
        ).scalar() or 0

        saidas = db.query(func.sum(models.StockMovement.quantidade)).filter(
            models.StockMovement.item_type_id == item.id,
            models.StockMovement.tipo.in_(["saida", "perda", "descarte"])
        ).scalar() or 0

        resultado.append(schemas.StockSummary(
            item_type_id=item.id,
            item_nome=item.nome,
            categoria=item.categoria,
            total_comprado=total_comprado,
            saldo_estoque=entradas - saidas
        ))

    return resultado


@router.delete("/{movimento_id}", status_code=204)
def deletar_movimento(movimento_id: int, db: Session = Depends(get_db)):
    movimento = db.query(models.StockMovement).filter(models.StockMovement.id == movimento_id).first()
    if not movimento:
        raise HTTPException(status_code=404, detail="Movimento não encontrado")
    db.delete(movimento)
    db.commit()
