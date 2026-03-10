from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ItemCategory(str, enum.Enum):
    CAMA = "cama"
    BANHO = "banho"
    MESA = "mesa"
    OUTROS = "outros"


class ItemType(Base):
    __tablename__ = "item_types"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)
    categoria = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchases = relationship("Purchase", back_populates="item_type")
    stock_movements = relationship("StockMovement", back_populates="item_type")
    laundry_records = relationship("LaundryRecord", back_populates="item_type")
    room_assignments = relationship("RoomAssignment", back_populates="item_type")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False)
    quantidade = Column(Integer, nullable=False)
    fornecedor = Column(String(200), nullable=True)
    valor_unitario = Column(Float, nullable=True)
    nota_fiscal = Column(String(100), nullable=True)
    observacoes = Column(Text, nullable=True)
    data_compra = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item_type = relationship("ItemType", back_populates="purchases")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # entrada, saida, ajuste
    quantidade = Column(Integer, nullable=False)
    motivo = Column(String(200), nullable=True)
    observacoes = Column(Text, nullable=True)
    data_movimento = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item_type = relationship("ItemType", back_populates="stock_movements")


class LaundryRecord(Base):
    __tablename__ = "laundry_records"

    id = Column(Integer, primary_key=True, index=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False)
    quantidade_enviada = Column(Integer, nullable=False, default=0)
    quantidade_retornada = Column(Integer, nullable=False, default=0)
    lavanderia_nome = Column(String(200), nullable=True)
    data_envio = Column(DateTime(timezone=True), nullable=False)
    data_retorno = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="pendente")  # pendente, parcial, completo
    observacoes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item_type = relationship("ItemType", back_populates="laundry_records")


class RoomAssignment(Base):
    __tablename__ = "room_assignments"

    id = Column(Integer, primary_key=True, index=True)
    item_type_id = Column(Integer, ForeignKey("item_types.id"), nullable=False)
    numero_quarto = Column(String(20), nullable=False)
    andar = Column(String(10), nullable=True)
    quantidade = Column(Integer, nullable=False)
    data_atribuicao = Column(DateTime(timezone=True), nullable=False)
    data_retirada = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Integer, nullable=False, default=1)  # 1=em uso, 0=retirado
    observacoes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item_type = relationship("ItemType", back_populates="room_assignments")


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    periodo_inicio = Column(DateTime(timezone=True), nullable=True)
    periodo_fim = Column(DateTime(timezone=True), nullable=True)
    relatorio_json = Column(Text, nullable=False)  # JSON com os dados
    analise_ia = Column(Text, nullable=True)
    total_comprado = Column(Integer, nullable=True)
    total_estoque = Column(Integer, nullable=True)
    total_lavanderia = Column(Integer, nullable=True)
    total_em_uso = Column(Integer, nullable=True)
    total_desfalque = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
