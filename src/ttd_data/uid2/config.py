from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IdentityScope(str, Enum):
    UID2 = "UID2"
    EUID = "EUID"


@dataclass
class UID2Config:
    base_url: str
    api_key: str
    client_secret: str
    identity_scope: IdentityScope
