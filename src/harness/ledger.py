"""Evidence ledger: the only fact store consumed by Verifier and Synthesizer."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


class EvidenceLedger:
    def __init__(self, items: Iterable[Dict[str, Any]] = ()):
        self._items: Dict[str, Dict[str, Any]] = {}
        for item in items:
            self.add(item)

    def add(self, item: Dict[str, Any]) -> Dict[str, Any]:
        evidence_id = str(item.get("evidence_id", "")).strip()
        if not evidence_id:
            raise ValueError("evidence_id is required")
        kind = item.get("kind", "measurement" if evidence_id.startswith("E") else "context")
        if kind not in {"measurement", "context"}:
            raise ValueError("kind must be measurement or context")
        normalized = {"evidence_id": evidence_id, "kind": kind, "query_id": item.get("query_id", "unknown"),
                      "status": item.get("status", "unavailable"), "data": item.get("data"),
                      "error": item.get("error"), "quality": item.get("quality", "unknown"),
                      "source": item.get("source", "unknown"), "params": dict(item.get("params") or {}),
                      "observed_at": item.get("observed_at"), "trace_id": item.get("trace_id", ""),
                      "error_kind": item.get("error_kind"), "attempts": int(item.get("attempts", 0) or 0),
                      "attempt": int(item.get("attempt", 1) or 1)}
        self._items[evidence_id] = normalized
        return normalized

    def all(self) -> List[Dict[str, Any]]:
        return list(self._items.values())

    def observed(self, query_id: str | None = None) -> List[Dict[str, Any]]:
        return [item for item in self._items.values()
                if item.get("status") == "observed" and (query_id is None or item.get("query_id") == query_id)]

    def measurement(self) -> List[Dict[str, Any]]:
        return [item for item in self.observed() if item.get("kind") == "measurement"]

    def context(self) -> List[Dict[str, Any]]:
        return [item for item in self.observed() if item.get("kind") == "context"]

    def has(self, query_id: str) -> bool:
        return bool(self.observed(query_id))

    def contains(self, evidence_id: str, *, observed_only: bool = False) -> bool:
        """Check an Evidence ID, distinct from ``has(query_id)``."""
        item = self._items.get(evidence_id)
        return item is not None and (not observed_only or item.get("status") == "observed")

    def missing(self, required_query_ids: Iterable[str]) -> List[str]:
        return [query_id for query_id in required_query_ids if not self.has(query_id)]

    def bind_claim(self, claim_id: str, evidence_ids: Iterable[str]) -> Dict[str, Any]:
        ids = list(evidence_ids)
        if not ids or any(evidence_id not in self._items for evidence_id in ids):
            raise ValueError(f"claim {claim_id} must reference existing evidence")
        if any(self._items[evidence_id].get("kind") != "measurement" for evidence_id in ids):
            raise ValueError(f"claim {claim_id} must reference measurement evidence")
        return {"claim_id": claim_id, "evidence_ids": ids}
