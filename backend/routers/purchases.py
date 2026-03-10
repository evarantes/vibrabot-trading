from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from database import get_db
import models, schemas

router = APIRouter(prefix="/purchases", tags=["Compras"])


@router.get("/", response_model=List[schemas.PurchaseOut])
def listar_compras(
    item_type_id: Optional[int] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Purchase).options(joinedload(models.Purchase.item_type))
    if item_type_id:
        query = query.filter(models.Purchase.item_type_id == item_type_id)
    if data_inicio:
        query = query.filter(models.Purchase.data_compra >= data_inicio)
    if data_fim:
        query = query.filter(models.Purchase.data_compra <= data_fim)
    return query.order_by(models.Purchase.data_compra.desc()).all()


@router.post("/", response_model=schemas.PurchaseOut, status_code=201)
def criar_compra(compra: schemas.PurchaseCreate, db: Session = Depends(get_db)):
    item = db.query(models.ItemType).filter(models.ItemType.id == compra.item_type_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tipo de item não encontrado")
    db_compra = models.Purchase(**compra.model_dump())
    db.add(db_compra)
    db.commit()
    db.refresh(db_compra)
    # Registrar automaticamente entrada no estoque
    movimento = models.StockMovement(
        item_type_id=compra.item_type_id,
        tipo="entrada",
        quantidade=compra.quantidade,
        motivo=f"Compra registrada - NF: {compra.nota_fiscal or 'N/A'}",
        data_movimento=compra.data_compra
    )
    db.add(movimento)
    db.commit()
    db.refresh(db_compra)
    return db_compra


@router.get("/{compra_id}", response_model=schemas.PurchaseOut)
def obter_compra(compra_id: int, db: Session = Depends(get_db)):
    compra = db.query(models.Purchase).options(
        joinedload(models.Purchase.item_type)
    ).filter(models.Purchase.id == compra_id).first()
    if not compra:
        raise HTTPException(status_code=404, detail="Compra não encontrada")
    return compra


@router.delete("/{compra_id}", status_code=204)
def deletar_compra(compra_id: int, db: Session = Depends(get_db)):
    compra = db.query(models.Purchase).filter(models.Purchase.id == compra_id).first()
    if not compra:
        raise HTTPException(status_code=404, detail="Compra não encontrada")
    db.delete(compra)
    db.commit()
