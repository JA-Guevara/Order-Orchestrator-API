"""Acceso a datos de pedidos: lectura de la vista y escritura de estados."""
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.pedido import PedidoEstado, PedidoPendiente
from app.shared.exceptions import NotFoundError


def _row_to_dict(obj: object) -> dict[str, object]:
    mapper = inspect(obj.__class__)
    return {col.key: getattr(obj, col.key) for col in mapper.column_attrs}


class PedidosRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_pendientes(self, *, limit: int = 100) -> list[dict[str, object]]:
        stmt = (
            select(PedidoPendiente)
            .order_by(PedidoPendiente.pedido_id)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_row_to_dict(row) for row in result.scalars().all()]

    async def update_estado(
        self,
        *,
        pedido_id: int,
        cambios: dict[str, str | None],
    ) -> dict[str, object]:
        registro = await self._session.get(PedidoEstado, pedido_id)
        if registro is None:
            raise NotFoundError(f"No existe registro de estado para el pedido {pedido_id}")
        for campo, valor in cambios.items():
            setattr(registro, campo, valor)
        await self._session.commit()
        return _row_to_dict(registro)