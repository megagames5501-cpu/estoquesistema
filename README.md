# Sistema de Estoque (LIFO) - Visual para Windows

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
- Windows (para uso com `start.bat`)

## Iniciar no Windows (visual)

1. Dê duplo clique no arquivo `start.bat`.
2. O sistema vai subir em `http://127.0.0.1:8000`.
3. A tela visual abre no navegador para você operar cadastros, entradas e saídas.

> O `start.bat` cria automaticamente `.venv` na primeira execução.

## Rodar manualmente

```bash
PYTHONPATH=src python -m estoquesistema.webapp
```

## CLI (opcional)

Também existe modo de linha de comando:

```bash
PYTHONPATH=src python -m estoquesistema.cli --help
```

## Testes

```bash
PYTHONPATH=src pytest -q
```
