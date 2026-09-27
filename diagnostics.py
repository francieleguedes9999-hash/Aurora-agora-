from __future__ import annotations
import re
from dataclasses import asdict, dataclass
from typing import Any

@dataclass
class Diagnostic:
    ok: bool
    kind: str
    summary: str
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    hints: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

_TRACE_RE = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)')
_COL_RE = re.compile(r'\bline (?P<line>\d+), column (?P<column>\d+)')


def diagnose(result: dict[str, Any]) -> dict[str, Any]:
    """Converte stdout/stderr de execução em um diagnóstico estável para o agente."""
    if result.get("ok") or result.get("passed"):
        return Diagnostic(True, "success", "Execução concluída", "Nenhum erro detectado", hints=[]).to_dict()

    text = "\n".join(x for x in (result.get("stderr"), result.get("stdout")) if x)
    low = text.lower()
    file = line = column = None
    matches = list(_TRACE_RE.finditer(text))
    if matches:
        m = matches[-1]
        file, line = m.group("file"), int(m.group("line"))
    cm = _COL_RE.search(text)
    if cm:
        column = int(cm.group("column"))

    if result.get("timed_out") or "timed out" in low or "timeout" in low:
        kind, summary, hints = "timeout", "Execução excedeu o tempo limite", [
            "Reduza a operação ou divida a tarefa em etapas menores.",
            "Verifique loops bloqueados e processos que não terminam.",
        ]
    elif "syntaxerror" in low or "indentationerror" in low:
        kind, summary, hints = "syntax", "Erro de sintaxe", [
            "Revise a linha indicada e o bloco imediatamente anterior.",
            "Verifique parênteses, aspas e indentação.",
        ]
    elif "modulenotfounderror" in low or "importerror" in low:
        kind, summary, hints = "import", "Falha ao importar módulo", [
            "Confirme se o módulo existe no projeto ou se a dependência foi declarada.",
            "Evite instalar dependências sem verificar o ambiente do projeto.",
        ]
    elif "filenotfounderror" in low or "no such file or directory" in low:
        kind, summary, hints = "file_not_found", "Arquivo ou diretório não encontrado", [
            "Confirme o caminho relativo ao workspace.",
            "Verifique se o arquivo foi criado antes de ser utilizado.",
        ]
    elif "assertionerror" in low or "assert " in low:
        kind, summary, hints = "assertion", "Teste ou condição de execução falhou", [
            "Compare o valor esperado com o valor observado.",
            "Corrija o comportamento do código antes de alterar o teste, salvo quando o teste estiver incorreto.",
        ]
    elif "typeerror" in low:
        kind, summary, hints = "type", "Operação recebeu um tipo ou argumento incompatível", [
            "Verifique os tipos e a assinatura da função na linha indicada.",
        ]
    elif "valueerror" in low:
        kind, summary, hints = "value", "Valor inválido para a operação", [
            "Valide a entrada antes de executar a operação.",
        ]
    elif "nameerror" in low:
        kind, summary, hints = "name", "Nome ou variável não definido", [
            "Verifique escopo, grafia e imports.",
        ]
    elif "keyerror" in low:
        kind, summary, hints = "key", "Chave inexistente", [
            "Verifique as chaves disponíveis antes de acessá-las.",
        ]
    else:
        kind, summary, hints = "unknown", "Falha de execução não classificada", [
            "Leia o traceback completo e reproduza o erro com a menor entrada possível.",
        ]

    lines = [x.strip() for x in text.splitlines() if x.strip()]
    message = lines[-1] if lines else "Comando falhou sem mensagem de erro."
    return Diagnostic(False, kind, summary, message, file, line, column, hints).to_dict()


class DiagnosticTool:
    def call(self, result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise TypeError("result deve ser um objeto JSON")
        return diagnose(result)
