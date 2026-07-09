from __future__ import annotations

import hashlib
import hmac
import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

ALLOWED_SCOPES: frozenset[str] = frozenset({
    "pedidos:read",
    "pedidos:reservar",
    "pedidos:cerrar",
})

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class APIClient(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    api_key_hash: str = Field(min_length=64, max_length=64)
    scopes: list[str]
    active: bool = True
    description: str = ""

    @field_validator("scopes")
    @classmethod
    def _scopes_must_be_known(cls, v: list[str]) -> list[str]:
        unknown = [s for s in v if s not in ALLOWED_SCOPES]
        if unknown:
            raise ValueError(f"Unknown scopes: {unknown}")
        return v


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    return path


@lru_cache(maxsize=1)
def _load_clients(path_str: str) -> list[APIClient]:
    path = _resolve_path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de clientes API en {path}. "
            "Crealo a partir de api_clients.example.json"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("api_clients.json debe ser una lista")
    clients = [APIClient.model_validate(item) for item in raw]
    ids = [c.id for c in clients]
    if len(ids) != len(set(ids)):
        raise ValueError("api_clients.json tiene IDs duplicados")
    return clients


def get_clients(path_str: str) -> list[APIClient]:
    return _load_clients(path_str)


def find_by_api_key(api_key: str, path_str: str) -> APIClient | None:
    if not api_key:
        return None
    provided_hash = _hash_api_key(api_key)
    for client in get_clients(path_str):
        if not client.active:
            continue
        if hmac.compare_digest(provided_hash, client.api_key_hash):
            return client
    return None