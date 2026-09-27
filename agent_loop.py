from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .tools.terminal import SafeTerminal
from .tools.test_runner import TestRunner

@dataclass
class Step:
    action: str
    result: dict

@dataclass
class ExecutionLoop:
    root: Path
    max_steps: int = 8
    history: list[Step] = field(default_factory=list)

    def execute(self, commands: list[str]) -> dict:
        terminal = SafeTerminal(self.root)
        for command in commands[:self.max_steps]:
            result = terminal.run(command)
            self.history.append(Step(command, result))
            if not result["ok"]:
                return {"ok": False, "stopped": "command_failed", "history": self.history}
        return {"ok": True, "stopped": "completed", "history": self.history}

    def test(self) -> dict:
        result = TestRunner(self.root).run()
        self.history.append(Step("python -m pytest -q", result))
        return result
