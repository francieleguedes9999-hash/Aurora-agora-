from __future__ import annotations
import ast, json, math, re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_]*")
IGNORE_DIRS = {'.aurora', '.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
TEXT_EXTS = {'.py','.js','.ts','.tsx','.jsx','.json','.md','.txt','.html','.css','.scss','.yaml','.yml','.toml','.sql','.sh'}

@dataclass
class ContextItem:
    kind: str
    path: str
    text: str
    score: float
    metadata: dict

class ProjectContext:
    """Small local lexical index for project-aware retrieval without embeddings."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.index_path = self.root / '.aurora' / 'context_index.jsonl'
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index: list[dict] = []
        self.load()

    def _tokens(self, text: str) -> set[str]:
        return {part.lower() for t in TOKEN_RE.findall(text) for part in t.split('_') if len(part) > 1}

    def _files(self) -> Iterable[Path]:
        for p in self.root.rglob('*'):
            if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
                continue
            if any(part in IGNORE_DIRS for part in p.relative_to(self.root).parts):
                continue
            yield p

    def _symbols(self, text: str, suffix: str) -> list[str]:
        if suffix != '.py':
            return []
        try:
            tree = ast.parse(text)
            out = []
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    out.append(n.name)
            return out[:80]
        except SyntaxError:
            return []

    def rebuild(self) -> int:
        entries = []
        for p in self._files():
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            rel = str(p.relative_to(self.root))
            entries.append({
                'path': rel,
                'suffix': p.suffix.lower(),
                'size': len(text),
                'tokens': sorted(self._tokens(rel + ' ' + text)),
                'symbols': self._symbols(text, p.suffix.lower()),
                'mtime_ns': p.stat().st_mtime_ns,
            })
        self._index = entries
        with self.index_path.open('w', encoding='utf-8') as f:
            for item in entries:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        return len(entries)

    def load(self) -> None:
        if not self.index_path.exists():
            self._index = []
            return
        out = []
        try:
            for line in self.index_path.read_text(encoding='utf-8').splitlines():
                if line.strip(): out.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            out = []
        self._index = out

    def _score(self, query: str, item: dict) -> float:
        q = self._tokens(query)
        if not q: return 0.0
        toks = set(item.get('tokens', []))
        overlap = len(q & toks)
        path_tokens = self._tokens(item.get('path', ''))
        path_overlap = len(q & path_tokens)
        symbol_overlap = len(q & {x.lower() for x in item.get('symbols', [])})
        return overlap + path_overlap * 2.5 + symbol_overlap * 3.0

    def search(self, query: str, limit: int = 8, max_chars: int = 1600) -> list[ContextItem]:
        if not self._index:
            self.rebuild()
        ranked = sorted(((self._score(query, x), x) for x in self._index), key=lambda z: z[0], reverse=True)
        results = []
        for score, item in ranked:
            if score <= 0: continue
            p = self.root / item['path']
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            qtokens = self._tokens(query)
            lines = text.splitlines()
            chosen = []
            for i, line in enumerate(lines):
                if qtokens & self._tokens(line):
                    chosen.extend(lines[max(0, i-1):min(len(lines), i+3)])
            snippet = '\n'.join(dict.fromkeys(chosen))[:max_chars]
            if not snippet:
                snippet = text[:max_chars]
            results.append(ContextItem('file', item['path'], snippet, round(score, 3), {
                'symbols': item.get('symbols', []), 'size': item.get('size', 0)
            }))
            if len(results) >= limit: break
        return results

    def format(self, query: str, limit: int = 6, max_total_chars: int = 7000) -> str:
        parts = []
        total = 0
        for item in self.search(query, limit):
            block = f"FILE: {item.path}\n{item.text}"
            if total + len(block) > max_total_chars:
                block = block[:max_total_chars-total]
            parts.append(block)
            total += len(block)
            if total >= max_total_chars: break
        return '\n\n---\n\n'.join(parts)
