from app.infrastructure.coordination.reservation_store import ReservationStore
from app.infrastructure.database.repositories.pedidos_repository import PedidosRepository
from app.shared.exceptions import AuthorizationError, ValidationError

CAMPOS_ACTUALIZABLES = frozenset({
    "estado_proceso",
    "estado_pedido",
    "pedido_sap",
    "observacion",
})


class PedidosService:
    def __init__(
        self,
        *,
        repository: PedidosRepository,
        reservations: ReservationStore,
        lease_seconds: int,
        max_candidatos: int,
    ) -> None:
        self._repository = repository
        self._reservations = reservations
        self._lease_seconds = lease_seconds
        self._max_candidatos = max_candidatos

    @property
    def lease_seconds(self) -> int:
        return self._lease_seconds

    async def list_pendientes(self, *, limit: int = 100) -> list[dict[str, object]]:
        return await self._repository.list_pendientes(limit=limit)

    async def reservar_siguiente(self, *, bot_id: str) -> dict[str, object] | None:
        candidatos = await self._repository.list_pendientes(limit=self._max_candidatos)
        for pedido in candidatos:
            reservado = await self._reservations.try_claim(
                pedido_id=int(pedido["pedido_id"]),
                bot_id=bot_id,
                lease_seconds=self._lease_seconds,
            )
            if reservado:
                return pedido
        return None

    async def renovar_lease(self, *, pedido_id: int, bot_id: str) -> None:
        renovado = await self._reservations.renew(
            pedido_id=pedido_id,
            bot_id=bot_id,
            lease_seconds=self._lease_seconds,
        )
        if not renovado:
            raise AuthorizationError(
                f"El pedido {pedido_id} no está reservado por este bot "
                "o el lease ya venció."
            )

    async def cerrar_pedido(
        self,
        *,
        pedido_id: int,
        bot_id: str,
        cambios: dict[str, str | None],
    ) -> dict[str, object]:
        owner = await self._reservations.owner(pedido_id=pedido_id)
        if owner is None:
            raise ValidationError(
                f"El pedido {pedido_id} no tiene reserva activa. "
                "El lease pudo haber vencido; el bot debe reservar de nuevo."
            )
        if owner != bot_id:
            raise AuthorizationError(
                f"El pedido {pedido_id} está reservado por otro bot."
            )

        cambios_validados = self._validar_cambios(cambios)
        resultado = await self._repository.update_estado(
            pedido_id=pedido_id,
            cambios=cambios_validados,
        )
        await self._reservations.release(pedido_id=pedido_id, bot_id=bot_id)
        return resultado

    def _validar_cambios(
        self, cambios: dict[str, str | None]
    ) -> dict[str, str | None]:
        filtrados = {
            campo: valor
            for campo, valor in cambios.items()
            if campo in CAMPOS_ACTUALIZABLES
        }
        estado_proceso = filtrados.get("estado_proceso")
        if not estado_proceso or not estado_proceso.strip():
            raise ValidationError("estado_proceso is required")
        filtrados["estado_proceso"] = estado_proceso.strip()
        return filtrados