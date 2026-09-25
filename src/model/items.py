"""Plain data classes for every list in the app (replaces model/items/*.java)."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum


class LabeledEnum(Enum):
    """Enum whose value is the label shown on its radio button (replaces EnumWithLabel)."""

    @property
    def label(self) -> str:
        return self.value


class PathType(LabeledEnum):
    FILE_NAMES_SEPARATE = "Provide file names separately"
    FILE_NAMES_IN_PATHS = "File names included in paths"


class PromoteType(LabeledEnum):
    COPY = "Copy"
    MOVE = "Move"


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class TodoItem:
    description: str
    additional_text: str = ""
    done: bool = False


@dataclass
class FolderItem:
    description: str
    path_to_open: str


@dataclass
class CopyItem:
    description: str
    text_to_copy: str


@dataclass
class InfoItem:
    description: str
    additional_text: str = ""


@dataclass
class SurroundItem:
    prefix: str = ""
    suffix: str = ""
    remove_final_suffix: bool = False

    @property
    def description(self) -> str:
        """Row text, e.g. ``'…',`` - shows what each line will be wrapped in."""
        text = f"{self.prefix}…{self.suffix}"
        return f"{text}   (no final separator)" if self.remove_final_suffix and self.suffix else text


@dataclass
class PromoteItem:
    description: str
    path_type: PathType = PathType.FILE_NAMES_SEPARATE
    promote_type: PromoteType = PromoteType.COPY
    file_names: list[str] = field(default_factory=list)
    origin_paths: list[str] = field(default_factory=list)
    destination_paths: list[str] = field(default_factory=list)


@dataclass
class ServerConfig:
    """One server tab of a SQL compare item (was ItemSQL)."""

    tab_name: str
    host: str
    port: int = -1  # -1 = use the driver's default port
    username: str = ""
    password: str = field(default="", repr=False)  # never persisted to JSON, see storage.py
    integrated_security: bool = False
    databases: list[str] = field(default_factory=list)


@dataclass
class SQLCompareItem:
    description: str
    procedure_name: str
    servers: list[ServerConfig] = field(default_factory=list)
    id: str = field(default_factory=_new_id)  # stable key for passwords in the OS keyring


@dataclass
class SchemaEnvironment:
    """A SQL Server + its databases, for the Schema Backup tab."""

    description: str
    server: str
    databases: list[str] = field(default_factory=list)
    connection_string: str = field(default="", repr=False)  # never persisted to JSON, see storage.py
    id: str = field(default_factory=_new_id)  # stable key for the connection string in the OS keyring


@dataclass
class SavedQuery:
    """A repeatable SQL Server query for the Queries tab."""

    description: str
    server: str
    query: str
    recent_databases: list[str] = field(default_factory=list)  # most recent first
    connection_string: str = field(default="", repr=False)  # never persisted to JSON, see storage.py
    id: str = field(default_factory=_new_id)  # stable key for the connection string in the OS keyring


# ---------------------------------------------------------------- (de)serialisation

_ENUM_FIELDS = {"path_type": PathType, "promote_type": PromoteType}


def item_to_dict(item) -> dict:
    data = asdict(item)
    for key, value in list(data.items()):
        if isinstance(value, Enum):
            data[key] = value.name
    if isinstance(item, SQLCompareItem):
        for server in data["servers"]:
            server.pop("password", None)
    if isinstance(item, (SchemaEnvironment, SavedQuery)):
        data.pop("connection_string", None)
    return data


def item_from_dict(cls, data: dict):
    data = dict(data)
    for key, enum_cls in _ENUM_FIELDS.items():
        if key in data:
            data[key] = enum_cls[data[key]]
    if cls is SQLCompareItem:
        data.pop("sql_type", None)  # older files: the app used to support MySQL too
        data["servers"] = [ServerConfig(**s) for s in data.get("servers", [])]
    return cls(**data)
