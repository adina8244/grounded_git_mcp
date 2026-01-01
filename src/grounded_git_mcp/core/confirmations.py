from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _now() -> int:
    return int(time.time())


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _stable_cmd_text(args: list[str]) -> str:
    return "\n".join(args)


@dataclass(frozen=True)
class Preconditions:
    expected_head: str | None = None
    expected_branch: str | None = None
    require_clean: bool = False
    require_no_conflicts: bool = True


@dataclass
class Confirmation:
    confirmation_id: str
    root: str
    args: list[str]
    classification: dict[str, Any]
    cmd_hash: str
    created_at: int
    expires_at: int
    max_uses: int = 1
    used: int = 0
    preconditions: Preconditions = Preconditions()

    def is_expired(self) -> bool:
        return _now() > self.expires_at

    def can_use(self) -> bool:
        return (not self.is_expired()) and self.used < self.max_uses


class FileConfirmationStore:
    """
    Minimal durable store:
      .grounded_git_mcp/confirmations.json
      .grounded_git_mcp/audit.jsonl
    """

    def __init__(self, repo_root: Path) -> None:
        self._dir = repo_root / ".grounded_git_mcp"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db = self._dir / "confirmations.json"
        self._audit = self._dir / "audit.jsonl"

        if not self._db.exists():
            self._db.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        return json.loads(self._db.read_text(encoding="utf-8") or "{}")

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self._db.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._db)

    def put(self, c: Confirmation) -> None:
        data = self._load()
        data[c.confirmation_id] = asdict(c)
        self._save(data)
        self.audit("proposed", c.confirmation_id, extra={"classification": c.classification})

    def get(self, confirmation_id: str) -> Confirmation | None:
        data = self._load()
        raw = data.get(confirmation_id)
        if not raw:
            return None
        raw["preconditions"] = Preconditions(**(raw.get("preconditions") or {}))
        return Confirmation(**raw)

    def mark_used(self, c: Confirmation, result: dict[str, Any]) -> None:
        data = self._load()
        raw = data.get(c.confirmation_id)
        if not raw:
            return
        raw["used"] = int(raw.get("used", 0)) + 1
        data[c.confirmation_id] = raw
        self._save(data)
        self.audit("executed", c.confirmation_id, extra={"result": result})

    def audit(self, action: str, confirmation_id: str, extra: dict[str, Any] | None = None) -> None:
        line = {
            "ts": _now(),
            "action": action,
            "confirmation_id": confirmation_id,
            **(extra or {}),
        }
        with self._audit.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def new_confirmation_id(root: Path, args: list[str]) -> str:
    # deterministic-ish id is fine, but still unique enough: time + hash
    seed = f"{root.resolve()}\n{_now()}\n{_stable_cmd_text(args)}"
    return _sha256_text(seed)[:16]


def command_hash(args: list[str]) -> str:
    return _sha256_text(_stable_cmd_text(args))
