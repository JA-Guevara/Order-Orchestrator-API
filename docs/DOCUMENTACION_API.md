# Documentacion de la API Itacamba

Esta documentacion describe el comportamiento real de la API segun el codigo actual del proyecto.

## 1. Proposito

La API expone una capa HTTP sobre una base de datos SQL Server y usa Redis para coordinar reservas temporales de pedidos entre bots.

El flujo principal es:

1. Un cliente se autentica con `X-API-Key`.
2. La API valida la API Key contra `api_clients.json`.
3. Si la clave es valida, emite un JWT firmado con HS256.
4. El bot usa ese JWT para consultar, reservar y cerrar pedidos.
5. Redis guarda la reserva temporal de cada pedido mientras dura el lease.

## 2. Arquitectura

La aplicacion sigue esta cadena de responsabilidad:

- `app/main.py`: crea la app FastAPI, registra handlers, CORS, rate limit y routers.
- `app/api/router.py`: compone los routers de autenticacion y pedidos.
- `app/api/endpoints/`: define los endpoints HTTP.
- `app/api/dependencies.py`: arma la inyeccion de dependencias para JWT, scopes, repositorios y servicios.
- `app/services/`: contiene la logica de negocio.
- `app/infrastructure/database/`: acceso a SQLAlchemy y SQL Server.
- `app/infrastructure/cache/`: cliente Redis.
- `app/infrastructure/security/`: validacion de API Keys y JWT.
- `app/infrastructure/coordination/`: almacenamiento de reservas en Redis.
- `app/shared/exceptions.py`: excepciones de dominio que luego se traducen a HTTP.

## 3. Punto de entrada

La aplicacion se construye en `app/main.py`.

Comportamientos importantes:

- `docs`, `redoc` y `openapi.json` solo se exponen fuera de produccion.
- Se registra `slowapi` para rate limiting.
- Si `CORS_ORIGINS` no esta vacio, se habilita CORS.
- En el startup se verifica Redis con `PING`.
- En el shutdown se cierra Redis y la engine de SQLAlchemy.

## 4. Autenticacion y autorizacion

### 4.1 API Key

La autenticacion inicial usa el header:

```http
X-API-Key: <api_key>
```

La API Key se valida contra `api_clients.json`.

Cada cliente debe tener:

- `id`
- `api_key_hash`
- `scopes`
- `active`
- `description`

La API Key nunca se compara en texto plano. Se calcula `sha256(api_key)` y se compara con `api_key_hash` usando comparacion segura.

### 4.2 JWT

Si la API Key es valida, la API emite un JWT con estos claims:

- `iss`: issuer configurado en `.env`
- `sub`: id del cliente
- `scopes`: lista de scopes del cliente
- `iat`: timestamp de emision
- `exp`: timestamp de expiracion
- `jti`: identificador unico del token

El JWT se firma con:

- algoritmo: `HS256`
- secreto: `JWT_SECRET`

### 4.3 Scope checking

La validacion de scopes ocurre en `app/api/dependencies.py`.

Regla actual:

- si el token tiene `*`, pasa cualquier chequeo
- si no, debe contener todos los scopes requeridos por el endpoint

### 4.4 Scopes vigentes

Los scopes permitidos actualmente son:

- `pedidos:read`
- `pedidos:reservar`
- `pedidos:cerrar`

## 5. Endpoints

Base path: el prefijo real depende de `API_PREFIX`.

### 5.1 POST `/api/v1/auth/token`

Obtiene un JWT para un cliente autenticado con `X-API-Key`.

Headers requeridos:

```http
X-API-Key: <api_key>
```

Respuesta exitosa:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800,
  "scopes": ["pedidos:reservar", "pedidos:cerrar"]
}
```

Errores tipicos:

- `401` si falta o es invalida la API Key
- `429` si supera el rate limit configurado

### 5.2 GET `/api/v1/auth/me`

Devuelve la identidad y los permisos del token actual.

Headers requeridos:

```http
Authorization: Bearer <jwt>
```

Respuesta:

```json
{
  "client_id": "bot_itacamba_01",
  "scopes": ["pedidos:reservar", "pedidos:cerrar"],
  "expires_in": 1250
}
```

### 5.3 POST `/api/v1/pedidos/reservar`

Reserva atomica el siguiente pedido pendiente disponible para el bot autenticado.

Scope requerido:

- `pedidos:reservar`

Comportamiento:

- busca candidatos en la vista `vw_pedidos_pendientes`
- intenta reservar cada pedido en Redis con un lease
- devuelve el primer pedido reservado con exito
- si no hay pedidos disponibles, devuelve `hay_pedido: false`

Respuesta con pedido reservado:

```json
{
  "hay_pedido": true,
  "lease_seconds": 300,
  "pedido": {
    "pedido_id": 123,
    "cliente_codigo": "C001",
    "cliente_nombre": "Cliente Demo",
    "centro_codigo": "01",
    "almacen_codigo": "A1",
    "monto_total": 1500.5,
    "estado_proceso": "pendiente"
  }
}
```

Respuesta sin pedido disponible:

```json
{
  "hay_pedido": false,
  "lease_seconds": null,
  "pedido": null
}
```

### 5.4 PATCH `/api/v1/pedidos/{pedido_id}/resultado`

Cierra un pedido reservado por el mismo bot que lo tomo.

Scope requerido:

- `pedidos:cerrar`

Path parameters:

- `pedido_id`: entero mayor que 0

Body:

```json
{
  "estado_proceso": "creado",
  "estado_pedido": "ok",
  "pedido_sap": "SAP-12345",
  "observacion": "Liberado por bot"
}
```

Reglas:

- `estado_proceso` es obligatorio
- `estado_proceso` no puede venir vacio
- solo se guardan los campos conocidos
- el pedido debe tener una reserva activa
- la reserva debe pertenecer al bot autenticado

Respuesta:

```json
{
  "pedido_id": 123,
  "estado_proceso": "creado",
  "estado_pedido": "ok",
  "pedido_sap": "SAP-12345",
  "observacion": "Liberado por bot"
}
```

### 5.5 GET `/api/v1/pedidos/pendientes`

Lista pedidos pendientes para monitoreo.

Scope requerido:

- `pedidos:read`

La respuesta es una lista de pedidos pendientes.

## 6. Negocio de pedidos

La logica vive en `app/services/pedidos_service.py`.

Reglas principales:

- `reservar_siguiente()` toma una lista de candidatos desde la base y prueba reservarlos uno por uno en Redis.
- `cerrar_pedido()` valida que el pedido siga reservado por el mismo bot antes de actualizar SQL Server.
- Si el lease vencio, el pedido vuelve a quedar disponible.
- Redis solo coordina la reserva temporal; el estado final vive en la base de datos.

## 7. Base de datos

La capa de acceso a datos usa SQLAlchemy async.

Archivos clave:

- `app/infrastructure/database/session.py`
- `app/infrastructure/database/repositories/pedidos_repository.py`
- `app/infrastructure/database/models/pedido.py`

Tablas y vistas referenciadas hoy:

- `vw_pedidos_pendientes`
- `pedido_estado`

## 8. Redis y reservas

Las reservas usan llaves con el prefijo configurado en `RESERVA_KEY_PREFIX`.

Comportamiento:

- `SET NX EX` crea la reserva de forma atomica
- `EX` define el lease
- si el proceso muere, la clave expira sola
- solo el bot propietario puede renovar o liberar la reserva

## 9. Errores HTTP

La API traduce excepciones de dominio a respuestas JSON con este formato:

```json
{
  "status": 400,
  "title": "Bad Request",
  "detail": "..."
}
```

Códigos relevantes:

- `400`: regla de negocio o validacion de dominio
- `401`: autenticacion invalida o ausente
- `403`: token valido pero sin scopes suficientes
- `404`: recurso no encontrado
- `422`: validacion de schema FastAPI/Pydantic
- `429`: rate limit excedido
- `500`: error no controlado

## 10. Rate limiting

El rate limiting esta habilitado con `slowapi` y depende de `RATE_LIMIT_ENABLED`.

Los endpoints que lo usan hoy son:

- `/auth/token`
- `/pedidos/reservar`
- `/pedidos/{pedido_id}/resultado`

La respuesta exitosa incluye headers de cuota restante y la respuesta bloqueada incluye `Retry-After`.

## 11. Configuracion obligatoria

La configuracion se carga desde `.env` y, segun el codigo actual, todas las variables son obligatorias.

Variables actuales:

- `APP_NAME`
- `APP_ENV`
- `DEBUG`
- `API_PREFIX`
- `DATABASE_URL`
- `DB_ECHO`
- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `REDIS_URL`
- `RESERVA_LEASE_SECONDS`
- `RESERVA_KEY_PREFIX`
- `RESERVA_MAX_CANDIDATOS`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `JWT_EXPIRE_MINUTES`
- `JWT_ISSUER`
- `API_CLIENTS_FILE`
- `CORS_ORIGINS`
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_AUTH`
- `RATE_LIMIT_RESERVAR`
- `RATE_LIMIT_RESULTADO`

Restricciones importantes:

- `JWT_SECRET` debe tener al menos 32 caracteres
- `JWT_ALGORITHM` solo acepta `HS256`
- `APP_ENV` solo acepta `development`, `staging` o `production`
- `CORS_ORIGINS` puede ser `*` o una lista separada por comas

## 12. Cliente de ejemplo

Archivo actual de referencia:

- `api_clients.json`

Ejemplo de cliente valido:

```json
[
  {
    "id": "bot_itacamba_01",
    "api_key_hash": "<sha256 de la api key>",
    "scopes": ["pedidos:reservar", "pedidos:cerrar"],
    "active": true,
    "description": "Bot RPA 01"
  }
]
```

## 13. Comandos utiles

### Crear hash de API Key

```bash
python scripts/generate_api_key_hash.py
```

### Ejecutar tests

```bash
pytest tests/ -v
```

## 14. Observaciones para Git

Este archivo esta pensado como documentacion de raiz para versionado en Git. Si cambian rutas, scopes o variables de entorno, conviene actualizarlo en el mismo cambio para evitar que la documentacion quede desalineada con la API real.
