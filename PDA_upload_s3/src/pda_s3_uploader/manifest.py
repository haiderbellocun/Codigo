from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any


@dataclass
class Manifest:
    uploaded: Dict[str, Any]

    @staticmethod
    def load(path: Path) -> "Manifest":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return Manifest(uploaded=data.get("uploaded", {}))
        return Manifest(uploaded={})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"uploaded": self.uploaded}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_uploaded(self, local_path: Path) -> bool:
        return local_path.as_posix() in self.uploaded

    def mark_uploaded(self, local_path: Path, *, bucket: str, key: str, size: int) -> None:
        self.uploaded[local_path.as_posix()] = {"bucket": bucket, "key": key, "size": size}
