#!/usr/bin/env python3
"""Aurora: create a functional application from a natural-language description."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from aurora.agent import Agent


def main() -> int:
    p = argparse.ArgumentParser(description='Aurora — gerador de aplicativos')
    p.add_argument('description', nargs='?', help='Descrição do aplicativo')
    p.add_argument('--name', help='Nome do aplicativo')
    p.add_argument('--workspace', default='workspace', help='Pasta de trabalho')
    p.add_argument('--no-tests', action='store_true', help='Não executar testes gerados')
    args = p.parse_args()
    description = (args.description or '').strip()
    if not description:
        description = input('Descreva o aplicativo: ').strip()
    if not description:
        print(json.dumps({'ok': False, 'error': 'Descrição vazia'}, ensure_ascii=False))
        return 2
    agent = Agent(workspace=args.workspace, max_steps=4)
    result = agent._call('app_build_coordinator', {
        'action': 'create_app', 'description': description, 'name': args.name,
        'run_tests': not args.no_tests, 'research': False,
    })
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get('ok') else 1

if __name__ == '__main__':
    raise SystemExit(main())
