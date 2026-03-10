from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from database import get_db
import models, schemas

router = APIRouter(prefix="/rooms", tags=["Quartos"])


@router.get("/", response_model=List[schemas.RoomAssignmentOut])
def listar_atribuicoes(
    numero_quarto: Optional[str] = None,
    item_type_id: Optional[int] = None,
    ativo: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.RoomAssignment).options(joinedload(models.RoomAssignment.item_type))
    if numero_quarto:
        query = query.filter(models.RoomAssignment.numero_quarto == numero_quarto)
    if item_type_id:
        query = query.filter(models.RoomAssignment.item_type_id == item_type_id)
    if ativo is not None:
        query = query.filter(models.RoomAssignment.ativo == ativo)
    return query.order_by(models.RoomAssignment.data_atribuicao.desc()).all()


@router.post("/", response_model=schemas.RoomAssignmentOut, status_code=201)
def criar_atribuicao(atribuicao: schemas.RoomAssignmentCreate, db: Session = Depends(get_db)):
    item = db.query(models.ItemType).filter(models.ItemType.id == atribuicao.item_type_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Tipo de item não encontrado")
    db_atribuicao = models.RoomAssignment(**atribuicao.model_dump())
    db.add(db_atribuicao)
    db.commit()
    db.refresh(db_atribuicao)
    return db_atribuicao


@router.patch("/{atribuicao_id}/retirar", response_model=schemas.RoomAssignmentOut)
def retirar_item_quarto(
    atribuicao_id: int,
    update: schemas.RoomAssignmentUpdate,
    db: Session = Depends(get_db)
):
    atribuicao = db.query(models.RoomAssignment).filter(
        models.RoomAssignment.id == atribuicao_id
    ).first()
    if not atribuicao:
        raise HTTPException(status_code=404, detail="Atribuição não encontrada")
    atribuicao.ativo = 0
    atribuicao.data_retirada = update.data_retirada or datetime.now()
    if update.observacoes:
        atribuicao.observacoes = update.observacoes
    db.commit()
    db.refresh(atribuicao)
    return atribuicao


@router.get("/em-uso/summary")
def resumo_em_uso(db: Session = Depends(get_db)):
    itens = db.query(models.ItemType).all()
    resultado = []
    for item in itens:
        total_em_uso = db.query(func.sum(models.RoomAssignment.quantidade)).filter(
            models.RoomAssignment.item_type_id == item.id,
            models.RoomAssignment.ativo == 1
        ).scalar() or 0

        resultado.append({
            "item_type_id": item.id,
            "item_nome": item.nome,
            "categoria": item.categoria,
            "total_em_uso": total_em_uso
        })

    return resultado


@router.get("/quartos")
def listar_quartos(db: Session = Depends(get_db)):
    quartos = db.query(
        models.RoomAssignment.numero_quarto,
        models.RoomAssignment.andar
    ).filter(
        models.RoomAssignment.ativo == 1
    ).distinct().all()
    return [{"numero_quarto": q[0], "andar": q[1]} for q in quartos]


@router.delete("/{atribuicao_id}", status_code=204)
def deletar_atribuicao(atribuicao_id: int, db: Session = Depends(get_db)):
    atribuicao = db.query(models.RoomAssignment).filter(
        models.RoomAssignment.id == atribuicao_id
    ).first()
    if not atribuicao:
        raise HTTPException(status_code=404, detail="Atribuição não encontrada")
    db.delete(atribuicao)
    db.commit()
