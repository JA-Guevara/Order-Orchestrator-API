# Itacamba API

API que expone una BD SQL Server existente al **bot de ventas Itacamba v3**
con autenticaciÃ³n **API Key â†’ JWT** y control de acceso por **scopes**.

## QuÃ© hace

- Emite un JWT corto a partir de una API Key (autenticaciÃ³n inicial).
- Lista pedidos pendientes y permite actualizar su estado, controlando
  permisos por scope del token.

## Flujo de autenticaciÃ³n

```text
1. Bot arranca
        â””â”€â–º POST /api/v1/auth/token
            header: X-API-Key: <api_key del bot>
        â—„â”€â”€â”€â”€ { access_token, expires_in, scopes }

2. Para cada request:
        â””â”€â–º GET /api/v1/pedidos/pendientes
            header: Authorization: Bearer <jwt>
        â—„â”€â”€â”€â”€ data

3. JWT expira (30 min) â†’ repite paso 1.
```

## Estructura

```text
Api-Itacamba/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  ├─ router.py
│  │  ├─ dependencies.py
│  │  ├─ error_handlers.py
│  │  ├─ endpoints/
│  │  │  ├─ auth.py
│  │  │  └─ pedidos.py
│  │  └─ schemas/
│  │     ├─ base.py
│  │     ├─ auth.py
│  │     └─ pedido.py
│  ├─ config/
│  │  └─ config.py
│  ├─ infrastructure/
│  │  ├─ database/
│  │  │  ├─ session.py
│  │  │  ├─ models/
│  │  │  │  ├─ base.py
│  │  │  │  ├─ pedido.py
│  │  │  │  └─ __init__.py
│  │  │  └─ repositories/
│  │  │     └─ pedidos_repository.py
│  │  └─ security/
│  │     ├─ auth_clients.py
│  │     └─ security.py
│  ├─ services/
│  │  ├─ auth_service.py
│  │  └─ pedidos_service.py
│  └─ shared/
│     └─ exceptions.py
├─ scripts/
│  └─ generate_api_key_hash.py
├─ api_clients.example.json
├─ .env.example
├─ requirements.txt
├─ README.md
└─ .gitignore
```

### Convencion de la capa `api/`

| Archivo / carpeta | Rol | Cuando se toca |
|---|---|---|
| `endpoints/` | **Contrato HTTP**. Cada archivo define rutas, payloads y status codes de un recurso. | Cada vez que agregas o cambias un endpoint. |
| `dependencies.py` | **Plomeria de inyeccion**. Construye sesion -> repo -> service y valida JWT/scopes. | Cuando agregas un nuevo repo/service o cambias la auth. |
| `error_handlers.py` | **Mapeo dominio -> HTTP**. Convierte excepciones internas en respuestas JSON. | Cuando agregas una excepcion nueva. |
| `router.py` | **Composicion**. Junta todos los routers de `endpoints/`. | Cuando agregas un endpoint nuevo (una linea mas). |

### Para agregar un endpoint nuevo

1. Crear `app/api/endpoints/<recurso>.py` con su `router = APIRouter(prefix="/<recurso>", tags=["<recurso>"])`.
2. Si necesita repo/service nuevos, agregarlos en `app/api/dependencies.py`.
3. En `app/api/router.py` agregar una linea: `api_router.include_router(<recurso>.router)`.

## Endpoints

| MÃ©todo | Ruta | Auth | Scope |
|---|---|---|---|
| `POST` | `/api/v1/auth/token` | header `X-API-Key` | â€” |
| `GET` | `/api/v1/auth/me` | `Authorization: Bearer` | â€” |
| `GET` | `/api/v1/pedidos/pendientes` | `Authorization: Bearer` | `pedidos:read` |
| `PATCH` | `/api/v1/pedidos/{id}/estado` | `Authorization: Bearer` | `pedidos:update` |

## CÃ³mo se administran los clientes

Cada consumidor (bot, panel, etc.) es una entrada en `api_clients.json`:

```json
[
  {
    "id": "bot_itacamba_v3",
    "api_key_hash": "<sha256 de la API key>",
    "scopes": ["pedidos:read", "pedidos:update"],
    "active": true,
    "description": "Bot principal de ventas"
  }
]
```

### Scopes disponibles

`pedidos:read`, `pedidos:update`, `pedidos:create`, `pedidos:validate`,
`pedidos:change_status`, `clientes:read`, `materiales:read`,
`comprobantes:read`, `comprobantes:upload`, y `*` (wildcard admin).

### Crear un cliente nuevo

```bash
python scripts/generate_api_key_hash.py
```

AnotÃ¡ la `API_KEY` (no se vuelve a mostrar). PegÃ¡ el `SHA256` en
`api_clients.json` como `api_key_hash`. ReiniciÃ¡ la API.

### Revocar un cliente

`"active": false` en su entrada y reiniciar. Los JWT vivos del cliente
quedan invÃ¡lidos al expirar (mÃ¡x. 30 min de exposiciÃ³n).

### Rotar la API Key de un cliente

GenerÃ¡ una nueva con el comando de arriba y reemplazÃ¡ `api_key_hash`.
ComunicÃ¡ al bot la nueva key. ReiniciÃ¡ la API.

### Rotar el JWT_SECRET

Cambialo en `.env` y reiniciÃ¡. **Todos** los JWT vivos se invalidan
inmediatamente â€” usar solo si sospechÃ¡s compromiso del secret.

## Ejemplos de consumo

**1) Obtener token:**
```http
POST /api/v1/auth/token HTTP/1.1
X-API-Key: t0DncelpTtNbG92PJ8J8LbcuQjmi4CSEQPWdZfsnjXkTZQM4w8mDSMpxrw3sBsWO
```
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "scopes": ["pedidos:read", "pedidos:update"]
}
```

**2) Consultar quiÃ©n soy:**
```http
GET /api/v1/auth/me
Authorization: Bearer <jwt>
```

**3) Listar pedidos pendientes:**
```http
GET /api/v1/pedidos/pendientes HTTP/1.1
Authorization: Bearer <jwt>
```

**4) Actualizar estado:**
```http
PATCH /api/v1/pedidos/123/estado HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "estado_proceso": "creado",
  "pedido_sap": "SAP-12345",
  "observacion": "Liberado por bot"
}
```

## Nombres de BD a ajustar

El acceso a datos usa el ORM de SQLAlchemy: no hay SQL escrito a mano.
Los nombres reales de la BD viven en un solo lugar, `app/infrastructure/database/models/pedido.py`:

- vista: `vw_pedidos_pendientes` (modelo `PedidoPendiente`)
- tabla: `pedido_estado` (modelo `PedidoEstado`)
- columnas: `pedido_id`, `cliente_codigo`, `cliente_nombre`, `estado`

CambiÃ¡ `__tablename__` y las columnas por los reales de tu BD; el
repositorio y el resto del cÃ³digo no se tocan.

## Variables de entorno

| Variable | Obligatoria | Default |
|---|---|---|
| `APP_NAME` | no | `ItacambaAPI` |
| `APP_ENV` | no | `development` |
| `DEBUG` | no | `false` |
| `API_PREFIX` | no | `/api/v1` |
| `DATABASE_URL` | **sÃ­** | â€” |
| `DB_ECHO` | no | `false` |
| `DB_POOL_SIZE` | no | `5` |
| `DB_MAX_OVERFLOW` | no | `10` |
| `JWT_SECRET` | **sÃ­** | â€” (â‰¥32 chars) |
| `JWT_ALGORITHM` | no | `HS256` |
| `JWT_EXPIRE_MINUTES` | no | `30` |
| `JWT_ISSUER` | no | `itacamba-api` |
| `API_CLIENTS_FILE` | no | `api_clients.json` |
| `CORS_ORIGINS` | no | `*` |

## Errores comunes

| CÃ³digo | Significado | Causa tÃ­pica |
|---|---|---|
| `401` | Unauthorized | API Key invÃ¡lida en `/auth/token`, JWT mal firmado, expirado, o ausente |
| `403` | Forbidden | JWT vÃ¡lido pero sin el scope requerido |
| `404` | Not Found | El recurso (ej. `pedido_id`) no existe |
| `422` | Unprocessable Entity | Body con campo extra o validaciÃ³n de schema fallÃ³ |
| `500` | Internal Server Error | Error no controlado (revisar logs de uvicorn) |




