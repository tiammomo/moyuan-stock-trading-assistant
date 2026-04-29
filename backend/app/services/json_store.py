from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from threading import RLock
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class JsonFileStore(Generic[T]):
    def __init__(self, path: Path, default_factory: Callable[[], T]):
        self.path = path
        self.default_factory = default_factory
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.write(self.default_factory())

    def read(self) -> T:
        with self._lock:
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                data = self.default_factory()
                self.write(data)
                return deepcopy(data)

    def write(self, data: T) -> None:
        with self._lock:
            tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_path.replace(self.path)

    def update(self, mutator: Callable[[T], T]) -> T:
        with self._lock:
            data = self.read()
            updated = mutator(data)
            self.write(updated)
            return updated
