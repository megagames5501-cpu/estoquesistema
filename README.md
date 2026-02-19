# Sistema de Estoque (LIFO)

Sistema de estoque em Python com persistência em SQLite para controlar:

- cadastro de categorias;
- cadastro de locais de armazenagem;
- cadastro de destinos de saída (para onde o insumo está indo);
- cadastro de insumos;
- entradas por lote;
- saídas por regra **LIFO** (último que entra, primeiro que sai);
- histórico completo de movimentações.

## Requisitos

- Python 3.10+

## Como executar

Use o módulo de CLI:

```bash
PYTHONPATH=src python -m estoquesistema.cli --help
```

### Exemplo rápido

```bash
PYTHONPATH=src python -m estoquesistema.cli nova-categoria "Resinas"
PYTHONPATH=src python -m estoquesistema.cli novo-local "Galpão A"
PYTHONPATH=src python -m estoquesistema.cli novo-destino "Produção Linha 1"
PYTHONPATH=src python -m estoquesistema.cli novo-insumo "Resina PP" kg 1 --estoque-minimo 50

PYTHONPATH=src python -m estoquesistema.cli entrada 1 1 100 --lote L1 --fornecedor FornecedorX
PYTHONPATH=src python -m estoquesistema.cli entrada 1 1 40 --lote L2

# Retirada LIFO (consome primeiro o lote mais novo)
PYTHONPATH=src python -m estoquesistema.cli saida 1 60 1 --local-id 1 --observacao "Ordem de produção OP-123"

PYTHONPATH=src python -m estoquesistema.cli estoque
PYTHONPATH=src python -m estoquesistema.cli movimentos
```

## Testes

```bash
PYTHONPATH=src pytest -q
```
