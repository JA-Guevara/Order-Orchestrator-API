from pydantic import Field

from app.api.schemas.base import APIModel


class PedidoPendienteRead(APIModel):

    pedido_id: int

    cliente_codigo: str | None = None
    cliente_nombre: str | None = None

    centro_codigo: str | None = None
    almacen_codigo: str | None = None

    monto_total: float | None = None

    estado_proceso: str | None = None


class PedidoReservadoResponse(APIModel):

    hay_pedido: bool
    lease_seconds: int | None = Field(
        default=None,
        description="Segundos de reserva exclusiva para el bot",
    )
    pedido: PedidoPendienteRead | None = None


class PedidoResultadoUpdate(APIModel):

    estado_proceso: str = Field(min_length=1, max_length=30)
    estado_pedido: str | None = Field(default=None, max_length=50)
    pedido_sap: str | None = Field(default=None, max_length=50)
    observacion: str | None = Field(default=None, max_length=500)


class PedidoResultadoResponse(APIModel):

    pedido_id: int
    estado_proceso: str
    estado_pedido: str | None = None
    pedido_sap: str | None = None
    observacion: str | None = None