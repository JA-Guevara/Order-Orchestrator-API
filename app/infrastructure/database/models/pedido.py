from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class PedidoPendiente(Base):
    __tablename__ = "vw_pedidos_pendientes"

    pedido_id: Mapped[int] = mapped_column(primary_key=True)


class PedidoEstado(Base):
    __tablename__ = "pedido_estado"

    pedido_id: Mapped[int] = mapped_column(primary_key=True)
    estado_proceso: Mapped[str]
    estado_pedido: Mapped[str | None]
    pedido_sap: Mapped[str | None]
    observacion: Mapped[str | None]