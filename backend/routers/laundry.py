from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from database import get_db
import models, schemas

router = APIRouter(prefix="/laundry", tags=["Lavanderia"])


@router.get("/", response_model=List[schemas.LaundryRecordOut])
def listar_registros(
    item_type_id: Optional[int] = None,
    status: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.LaundryRecord).options(joinedload(models.LaundryRecord.item_type))
    if item_type_id:
        query = query.filter(models.LaundryRecord.item_type_id == item_type_id)
    if status:
        query = query.filter(models.LaundryRecord.status == status)
    if data_inicio:
        query = query.filter(models.LaundryRecord.data_envio >= data_inicio)
    if data_fim:
        query = query.filter(models.LaundryRecord.data_envio <= data_fim)
    return query.order_by(models.LaundryRecord.data_envio.desc()).all()


@router.post("/", response_model=schemas.LaundryRecordOut, status_code=201)
def criar_registro(registro: schemas.LaundryRecordCreate, db: Session = Depends(get_db)):
    item = db.query(models.ItemType).filter(models.ItemType.id == registro.item_type_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tipo de item não encontrado")
    db_registro = models.LaundryRecord(**registro.model_dump())
    db.add(db_registro)
    db.commit()
    db.refresh(db_registro)
    return db_registro


@router.patch("/{registro_id}/retorno", response_model=schemas.LaundryRecordOut)
def registrar_retorno(
    registro_id: int,
    update: schemas.LaundryRecordUpdate,
    db: Session = Depends(get_db)
):
    registro = db.query(models.LaundryRecord).filter(models.LaundryRecord.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")

    if update.quantidade_retornada is not None:
        registro.quantidade_retornada = update.quantidade_retornada
        if update.quantidade_retornada >= registro.quantidade_enviada:
            registro.status = "completo"
        elif update.quantidade_retornada > 0:
            registro.status = "parcial"
    if update.data_retorno is not None:
        registro.data_retorno = update.data_retorno
    if update.status is not None:
        registro.status = update.status
    if update.observacoes is not None:
        registro.observacoes = update.observacoes

    db.commit()
    db.refresh(registro)
    return registro


@router.get("/pendentes", response_model=List[schemas.LaundryRecordOut])
def listar_pendentes(db: Session = Depends(get_db)):
    return db.query(models.LaundryRecord).options(
        joinedload(models.LaundryRecord.item_type)
    ).filter(
        models.LaundryRecord.status.in_(["pendente", "parcial"])
    ).order_by(models.LaundryRecord.data_envio.asc()).all()


@router.get("/summary")
def resumo_lavanderia(db: Session = Depends(get_db)):
    itens = db.query(models.ItemType).all()
    resultado = []
    for item in itens:
        total_enviado = db.query(func.sum(models.LaundryRecord.quantidade_enviada)).filter(
            models.LaundryRecord.item_type_id == item.id
        ).scalar() or 0

        total_retornado = db.query(func.sum(models.LaundryRecord.quantidade_retornada)).filter(
            models.LaundryRecord.item_type_id == item.id
        ).scalar() or 0

        na_lavanderia = db.query(func.sum(
            models.LaundryRecord.quantidade_enviada - models.LaundryRecord.quantidade_retornada
        )).filter(
            models.LaundryRecord.item_type_id == item.id,
            models.LaundryRecord.status.in_(["pendente", "parcial"])
        ).scalar() or 0

        resultado.append({
            "item_type_id": item.id,
            "item_nome": item.nome,
            "categoria": item.categoria,
            "total_enviado": total_enviado,
            "total_retornado": total_retornado,
            "atualmente_na_lavanderia": na_lavanderia,
            "diferenca": total_enviado - total_retornado
        })

    return resultado


@router.delete("/{registro_id}", status_code=204)
def deletar_registro(registro_id: int, db: Session = Depends(get_db)):
    registro = db.query(models.LaundryRecord).filter(models.LaundryRecord.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    db.delete(registro)
    db.commit()
