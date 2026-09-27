"""Aurora Training Lab: ingest and organize multimodal learning material.

This layer intentionally separates training material from operational memory. It
stores metadata, normalized text/chunks and references to media. Actual model
fine-tuning remains provider-specific; the lab can export curated JSONL datasets
or supply retrieved context to the cognitive brain.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class TrainingLab:
    SUPPORTED_KINDS = {"text", "article", "topic", "audio", "voice", "video", "document"}

    def __init__(self, root: str = ".aurora/training_lab"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"
        self.manifest = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            return {"version": 1, "items": [], "datasets": []}
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "items": [], "datasets": []}

    def _save(self) -> None:
        tmp = self.manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.manifest_path)

    @staticmethod
    def _id(kind: str, title: str, content: str = "") -> str:
        raw = f"{kind}|{title}|{content}|{time.time_ns()}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    @staticmethod
    def _words(text: str) -> set[str]:
        return {w for w in re.findall(r"[\wÀ-ÿ]+", text.lower()) if len(w) > 2}

    def add(self, kind: str, title: str, content: str = "", *, source: str = "",
            tags: Optional[Iterable[str]] = None, metadata: Optional[Dict[str, Any]] = None,
            path: str = "", transcript: str = "", license: str = "") -> Dict[str, Any]:
        kind = kind.lower().strip()
        if kind not in self.SUPPORTED_KINDS:
            raise ValueError(f"tipo não suportado: {kind}")
        item = {
            "id": self._id(kind, title, content or transcript),
            "kind": kind,
            "title": title,
            "content": content,
            "transcript": transcript,
            "source": source,
            "path": path,
            "tags": list(tags or []),
            "metadata": dict(metadata or {}),
            "license": license,
            "created_at": time.time(),
        }
        if path:
            p = Path(path)
            item["media"] = {
                "exists": p.exists(),
                "size": p.stat().st_size if p.exists() else None,
                "mime": mimetypes.guess_type(str(p))[0],
                "extension": p.suffix.lower(),
            }
        self.manifest["items"].append(item)
        self._save()
        return item

    def add_file(self, path: str, *, kind: Optional[str] = None, title: Optional[str] = None,
                 tags: Optional[Iterable[str]] = None, transcript: str = "",
                 license: str = "") -> Dict[str, Any]:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(path)
        detected = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        ext = p.suffix.lower()
        if kind is None:
            if detected.startswith("video/"):
                kind = "video"
            elif detected.startswith("audio/"):
                kind = "voice"
            elif detected.startswith("text/") or ext in {".md", ".rst", ".json", ".csv"}:
                kind = "document"
            else:
                kind = "document"
        content = ""
        if kind in {"text", "article", "topic", "document"} and (detected.startswith("text/") or ext in {".txt", ".md", ".rst", ".csv", ".json"}):
            content = p.read_text(encoding="utf-8", errors="replace")
        return self.add(kind, title or p.name, content, path=str(p), tags=tags,
                        transcript=transcript, license=license,
                        metadata={"mime": detected})

    def add_article_url(self, url: str, *, title: Optional[str] = None,
                        tags: Optional[Iterable[str]] = None, license: str = "") -> Dict[str, Any]:
        req = urllib.request.Request(url, headers={"User-Agent": "Aurora-TrainingLab/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
        # Lightweight HTML normalization; deeper extraction can be supplied by a provider.
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", raw, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return self.add("article", title or url, text, source=url, tags=tags, license=license,
                        metadata={"retrieved": True})

    def list(self, kind: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        items = self.manifest["items"]
        if kind:
            items = [x for x in items if x["kind"] == kind]
        if tag:
            items = [x for x in items if tag in x.get("tags", [])]
        return items

    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        return next((x for x in self.manifest["items"] if x["id"] == item_id), None)

    def search(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        q = self._words(query)
        scored = []
        for item in self.manifest["items"]:
            hay = " ".join([item.get("title", ""), item.get("content", ""),
                             item.get("transcript", ""), " ".join(item.get("tags", []))])
            words = self._words(hay)
            score = len(q & words)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], -pair[1].get("created_at", 0)))
        return [item for _, item in scored[:limit]]

    def context(self, query: str, limit: int = 5, max_chars: int = 8000) -> str:
        parts = []
        total = 0
        for item in self.search(query, limit):
            text = item.get("content") or item.get("transcript") or ""
            block = f"[{item['kind']}] {item['title']}\n{text[:2500]}"
            if item.get("source"):
                block += f"\nFonte: {item['source']}"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n\n".join(parts)

    def export_dataset(self, name: str = "aurora_training") -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._") or "aurora_training"
        path = self.root / f"{safe}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for item in self.manifest["items"]:
                text = item.get("content") or item.get("transcript")
                if not text:
                    continue
                fh.write(json.dumps({
                    "id": item["id"], "title": item["title"], "text": text,
                    "kind": item["kind"], "source": item.get("source", ""),
                    "tags": item.get("tags", []), "license": item.get("license", "")
                }, ensure_ascii=False) + "\n")
        if name not in self.manifest["datasets"]:
            self.manifest["datasets"].append(name)
            self._save()
        return str(path)

    def status(self) -> Dict[str, Any]:
        counts = {k: len(self.list(k)) for k in sorted(self.SUPPORTED_KINDS)}
        return {
            "items": len(self.manifest["items"]),
            "by_kind": counts,
            "datasets": list(self.manifest["datasets"]),
            "path": str(self.root),
            "multimodal": {"video": counts.get("video", 0), "audio_voice": counts.get("audio", 0) + counts.get("voice", 0)},
        }
