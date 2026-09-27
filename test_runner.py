from __future__ import annotations
from pathlib import Path
from .terminal import SafeTerminal
from ..diagnostics import diagnose

class TestRunner:
    __test__ = False
    def __init__(self, root: str | Path):
        self.terminal = SafeTerminal(root)

    def run(self, command: str | None = None) -> dict:
        result = self.terminal.run(command or "python -m pytest -q")
        result["passed"] = result["ok"]
        result["diagnostic"] = diagnose(result)
        return result
