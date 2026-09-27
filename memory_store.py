from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

@dataclass
class Memory:
    id: int
    kind: str
    text: str
    tags: list[str]
    created_at: str
    metadata: dict[str, Any]

class LongTermMemory:
    """Small persistent, local memory store for Aurora projects."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'memory.jsonl'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[Memory]:
        if not self.path.exists():
            return []
        out=[]
        for line in self.path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try: out.append(Memory(**json.loads(line)))
                except (TypeError, ValueError, json.JSONDecodeError): pass
        return out

    def remember(self, text: str, kind: str='fact', tags: list[str] | None=None, metadata: dict[str, Any] | None=None) -> Memory:
        memories=self._load()
        item=Memory(len(memories)+1, kind, text.strip(), tags or [], datetime.now(timezone.utc).isoformat(), metadata or {})
        with self.path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(item), ensure_ascii=False)+'\n')
        return item

    def search(self, query: str, limit: int=8) -> list[Memory]:
        terms=[t.lower() for t in re.findall(r'[\wÀ-ÿ]+', query) if len(t)>1]
        scored=[]
        for m in self._load():
            hay=(m.text+' '+' '.join(m.tags)+' '+m.kind).lower()
            score=sum(hay.count(t) for t in terms)
            if score: scored.append((score,m))
        scored.sort(key=lambda x:(x[0], x[1].id), reverse=True)
        return [m for _,m in scored[:max(1,limit)]]

    def recent(self, limit: int=8) -> list[Memory]:
        return self._load()[-max(1,limit):][::-1]

    def export(self) -> list[dict[str, Any]]:
        return [asdict(m) for m in self._load()]
