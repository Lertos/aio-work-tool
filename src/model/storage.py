"""JSON persistence, one file per list (replaces DataFile/FileManager and the .ser files).

File format::

    {"version": 1, "active": [...], "history": [...]}

* Writes are atomic: data goes to a temp file first, then replaces the real
  file, so a crash mid-save can never leave a half-written list.
* SQL passwords are never written to JSON. They go to the OS credential
  store (Windows Credential Manager) through the ``keyring`` package.
* A corrupt file is renamed to ``<name>.json.bad`` and the list starts empty,
  so one broken file can't stop the app from opening.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Protocol

from .item_store import ItemStore
from .items import (CopyItem, FolderItem, InfoItem, PromoteItem, SQLCompareItem,
                    TodoItem, item_from_dict, item_to_dict)

SCHEMA_VERSION = 1
KEYRING_SERVICE = "work-aio-tool"

LIST_FILES = {
    "todo": TodoItem,
    "folders": FolderItem,
    "copy": CopyItem,
    "promote": PromoteItem,
    "info": InfoItem,
    "sql_compare": SQLCompareItem,
}


class SecretStore(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...


class KeyringSecrets:
    """Passwords in the OS credential store."""

    def __init__(self, service: str = KEYRING_SERVICE) -> None:
        import keyring  # imported here so tests and the rest of the model don't need it
        self._keyring = keyring
        self._service = service

    def get(self, key: str) -> str | None:
        return self._keyring.get_password(self._service, key)

    def set(self, key: str, value: str) -> None:
        self._keyring.set_password(self._service, key, value)

    def delete(self, key: str) -> None:
        try:
            self._keyring.delete_password(self._service, key)
        except self._keyring.errors.PasswordDeleteError:
            pass


class MemorySecrets:
    """In-memory stand-in for tests."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)


def _secret_key(item: SQLCompareItem, tab_name: str) -> str:
    return f"{item.id}/{tab_name}"


class Storage:
    def __init__(self, data_dir: Path | str, secrets: SecretStore) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.secrets = secrets

    # ------------------------------------------------------------------- public
    def load_all(self) -> dict[str, ItemStore]:
        return {name: self.load(name) for name in LIST_FILES}

    def load(self, name: str) -> ItemStore:
        cls = LIST_FILES[name]
        path = self._path(name)
        active, history = [], []
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                active = [item_from_dict(cls, d) for d in raw.get("active", [])]
                history = [item_from_dict(cls, d) for d in raw.get("history", [])]
            except (ValueError, KeyError, TypeError):
                path.replace(path.with_suffix(".json.bad"))
                active, history = [], []
        if cls is SQLCompareItem:
            for item in active + history:
                self._load_passwords(item)
        return ItemStore(active, history, save=lambda store, n=name: self.save(n, store))

    def save(self, name: str, store: ItemStore) -> None:
        if LIST_FILES[name] is SQLCompareItem:
            self._sync_passwords(store)
        payload = {
            "version": SCHEMA_VERSION,
            "active": [item_to_dict(i) for i in store.active],
            "history": [item_to_dict(i) for i in store.history],
        }
        self._atomic_write(self._path(name), json.dumps(payload, indent=2))

    # ------------------------------------------------------------------ helpers
    def _path(self, name: str) -> Path:
        return self.data_dir / f"{name}.json"

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def _load_passwords(self, item: SQLCompareItem) -> None:
        for server in item.servers:
            if not server.integrated_security:
                server.password = self.secrets.get(_secret_key(item, server.tab_name)) or ""

    def _sync_passwords(self, store: ItemStore) -> None:
        # Items still in history keep their passwords so "Undo Delete" works.
        for item in store.active + store.history:
            for server in item.servers:
                key = _secret_key(item, server.tab_name)
                if server.password and not server.integrated_security:
                    self.secrets.set(key, server.password)
                else:
                    self.secrets.delete(key)
