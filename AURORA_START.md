# Aurora — início rápido

Aurora recebe uma descrição em linguagem natural e cria um aplicativo funcional.

## Criar um aplicativo

```bash
python aurora_cli.py "Crie um aplicativo de tarefas com cadastro, busca, edição e exclusão"
```

Opcionalmente:

```bash
python aurora_cli.py "Crie uma loja de produtos com catálogo e carrinho" --name MinhaLoja --workspace workspace
```

O resultado é criado dentro de `workspace/apps/`, com frontend, backend quando necessário, banco, testes, preview e contrato.

## Fluxo automático

**descrição → blueprint → construção → testes → quality gate → preview → validação → entrega**

A execução é local por padrão e não exige API externa para esse fluxo básico.
