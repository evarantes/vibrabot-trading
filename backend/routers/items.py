from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models, schemas

router = APIRouter(prefix="/items", tags=["Tipos de Enxoval"])


@router.get("/", response_model=List[schemas.ItemTypeOut])
def listar_itens(db: Session = Depends(get_db)):
    return db.query(models.ItemType).order_by(models.ItemType.categoria, models.ItemType.nome).all()


@router.post("/", response_model=schemas.ItemTypeOut, status_code=201)
def criar_item(item: schemas.ItemTypeCreate, db: Session = Depends(get_db)):
    existente = db.query(models.ItemType).filter(models.ItemType.nome == item.nome).first()
    if existente:
        raise HTTPException(status_code=400, detail="Item com este nome já existe")
    db_item = models.ItemType(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/{item_id}", response_model=schemas.ItemTypeOut)
def obter_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.ItemType).filter(models.ItemType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.put("/{item_id}", response_model=schemas.ItemTypeOut)
def atualizar_item(item_id: int, item: schemas.ItemTypeCreate, db: Session = Depends(get_db)):
    db_item = db.query(models.ItemType).filter(models.ItemType.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    for key, value in item.model_dump().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}", status_code=204)
def deletar_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.ItemType).filter(models.ItemType.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(db_item)
    db.commit()
