"""Modelos ORM (SQLAlchemy declarativo).

La BD ya existe: estos modelos solo *mapean* tablas/vistas reales,
no las crean. Ajustar __tablename__ y columnas a los nombres reales.
"""
from app.infrastructure.database.models.base import Base
from app.infrastructure.database.models.pedido import PedidoEstado, PedidoPendiente

__all__ = ["Base", "PedidoEstado", "PedidoPendiente"]

