from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── ItemType ──────────────────────────────────────────────────────────────────

class ItemTypeBase(BaseModel):
    nome: str
    categoria: str
    descricao: Optional[str] = None


class ItemTypeCreate(ItemTypeBase):
    pass


class ItemTypeOut(ItemTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Purchase ──────────────────────────────────────────────────────────────────

class PurchaseBase(BaseModel):
    item_type_id: int
    quantidade: int
    fornecedor: Optional[str] = None
    valor_unitario: Optional[float] = None
    nota_fiscal: Optional[str] = None
    observacoes: Optional[str] = None
    data_compra: datetime


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseOut(PurchaseBase):
    id: int
    created_at: datetime
    item_type: Optional[ItemTypeOut] = None

    class Config:
        from_attributes = True


# ── StockMovement ─────────────────────────────────────────────────────────────

class StockMovementBase(BaseModel):
    item_type_id: int
    tipo: str  # entrada, saida, ajuste
    quantidade: int
    motivo: Optional[str] = None
    observacoes: Optional[str] = None
    data_movimento: datetime


class StockMovementCreate(StockMovementBase):
    pass


class StockMovementOut(StockMovementBase):
    id: int
    created_at: datetime
    item_type: Optional[ItemTypeOut] = None

    class Config:
        from_attributes = True


class StockSummary(BaseModel):
    item_type_id: int
    item_nome: str
    categoria: str
    total_comprado: int
    saldo_estoque: int


# ── LaundryRecord ─────────────────────────────────────────────────────────────

class LaundryRecordBase(BaseModel):
    item_type_id: int
    quantidade_enviada: int
    quantidade_retornada: int = 0
    lavanderia_nome: Optional[str] = None
    data_envio: datetime
    data_retorno: Optional[datetime] = None
    status: str = "pendente"
    observacoes: Optional[str] = None


class LaundryRecordCreate(LaundryRecordBase):
    pass


class LaundryRecordUpdate(BaseModel):
    quantidade_retornada: Optional[int] = None
    data_retorno: Optional[datetime] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None


class LaundryRecordOut(LaundryRecordBase):
    id: int
    created_at: datetime
    item_type: Optional[ItemTypeOut] = None

    class Config:
        from_attributes = True


# ── RoomAssignment ────────────────────────────────────────────────────────────

class RoomAssignmentBase(BaseModel):
    item_type_id: int
    numero_quarto: str
    andar: Optional[str] = None
    quantidade: int
    data_atribuicao: datetime
    data_retirada: Optional[datetime] = None
    ativo: int = 1
    observacoes: Optional[str] = None


class RoomAssignmentCreate(RoomAssignmentBase):
    pass


class RoomAssignmentUpdate(BaseModel):
    data_retirada: Optional[datetime] = None
    ativo: Optional[int] = None
    observacoes: Optional[str] = None


class RoomAssignmentOut(RoomAssignmentBase):
    id: int
    created_at: datetime
    item_type: Optional[ItemTypeOut] = None

    class Config:
        from_attributes = True


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    titulo: str
    periodo_inicio: Optional[datetime] = None
    periodo_fim: Optional[datetime] = None


class AuditItemDetail(BaseModel):
    item_type_id: int
    item_nome: str
    categoria: str
    total_comprado: int
    total_estoque: int
    total_na_lavanderia: int
    total_em_uso: int
    total_contabilizado: int
    desfalque: int
    percentual_desfalque: float


class AuditReportOut(BaseModel):
    id: int
    titulo: str
    periodo_inicio: Optional[datetime]
    periodo_fim: Optional[datetime]
    relatorio_json: str
    analise_ia: Optional[str]
    total_comprado: Optional[int]
    total_estoque: Optional[int]
    total_lavanderia: Optional[int]
    total_em_uso: Optional[int]
    total_desfalque: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_tipos_item: int
    total_comprado: int
    total_estoque: int
    total_na_lavanderia: int
    total_em_uso: int
    total_desfalque: int
    percentual_desfalque: float
    alertas: List[str]
    ultimas_auditorias: List[AuditReportOut]
