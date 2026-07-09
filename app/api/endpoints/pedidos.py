"""Endpoints de pedidos: reserva atómica y cierre, identidad desde JWT."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response

from app.api.dependencies import BotIdDep, PedidosServiceDep, require_scopes
from app.api.rate_limit import limiter
from app.api.schemas.pedido import (
    PedidoPendienteRead,
    PedidoReservadoResponse,
    PedidoResultadoResponse,
    PedidoResultadoUpdate,
)
from app.config.config import get_settings

router = APIRouter(prefix="/pedidos", tags=["pedidos"])
_settings = get_settings()


@router.post(
    "/reservar",
    response_model=PedidoReservadoResponse,
    summary="Reservar atómicamente el siguiente pedido pendiente para el bot autenticado",
    dependencies=[Depends(require_scopes("pedidos:reservar"))],
)
@limiter.limit(_settings.rate_limit_reservar)
async def reservar_pedido(
    request: Request,
    response: Response,
    bot_id: BotIdDep,
    service: PedidosServiceDep,
) -> PedidoReservadoResponse:
    pedido = await service.reservar_siguiente(bot_id=bot_id)

    if pedido is None:
        return PedidoReservadoResponse(hay_pedido=False)

    return PedidoReservadoResponse(
        hay_pedido=True,
        lease_seconds=service.lease_seconds,
        pedido=PedidoPendienteRead.model_validate(pedido),
    )


@router.patch(
    "/{pedido_id}/resultado",
    response_model=PedidoResultadoResponse,
    summary="Cerrar un pedido reservado (solo el bot dueño del lease)",
    dependencies=[Depends(require_scopes("pedidos:cerrar"))],
)
@limiter.limit(_settings.rate_limit_resultado)
async def cerrar_pedido(
    request: Request,
    response: Response,
    pedido_id: Annotated[int, Path(gt=0)],
    payload: PedidoResultadoUpdate,
    bot_id: BotIdDep,
    service: PedidosServiceDep,
) -> PedidoResultadoResponse:
    resultado = await service.cerrar_pedido(
        pedido_id=pedido_id,
        bot_id=bot_id,
        cambios=payload.model_dump(exclude_unset=True),
    )

    return PedidoResultadoResponse.model_validate(resultado)


@router.get(
    "/pendientes",
    response_model=list[PedidoPendienteRead],
    summary="Listar pedidos pendientes (monitoreo)",
    dependencies=[Depends(require_scopes("pedidos:read"))],
)
async def listar_pendientes(
    service: PedidosServiceDep,
) -> list[PedidoPendienteRead]:
    items = await service.list_pendientes(limit=100)
    return [PedidoPendienteRead.model_validate(item) for item in items]