from __future__ import annotations

import argparse
from pathlib import Path

from .inventory import InventorySystem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sistema de estoque com retirada LIFO")
    parser.add_argument("--db", default="estoque.db", help="Caminho para o arquivo SQLite")

    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("nova-categoria", help="Criar categoria")
    c.add_argument("nome")
    c.add_argument("--descricao", default="")

    l = sub.add_parser("novo-local", help="Criar local de armazenagem")
    l.add_argument("nome")
    l.add_argument("--descricao", default="")

    d = sub.add_parser("novo-destino", help="Criar destino de saída")
    d.add_argument("nome")
    d.add_argument("--descricao", default="")

    i = sub.add_parser("novo-insumo", help="Criar item/insumo")
    i.add_argument("nome")
    i.add_argument("unidade")
    i.add_argument("categoria_id", type=int)
    i.add_argument("--estoque-minimo", type=float, default=0)

    e = sub.add_parser("entrada", help="Registrar entrada de lote")
    e.add_argument("item_id", type=int)
    e.add_argument("local_id", type=int)
    e.add_argument("quantidade", type=float)
    e.add_argument("--lote", default="")
    e.add_argument("--fornecedor", default="")
    e.add_argument("--custo-unitario", type=float)
    e.add_argument("--observacao", default="")

    s = sub.add_parser("saida", help="Registrar saída LIFO")
    s.add_argument("item_id", type=int)
    s.add_argument("quantidade", type=float)
    s.add_argument("destino_id", type=int)
    s.add_argument("--local-id", type=int)
    s.add_argument("--observacao", default="")

    sub.add_parser("estoque", help="Exibir posição de estoque")
    sub.add_parser("movimentos", help="Exibir histórico")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    db = Path(args.db)
    system = InventorySystem(db)

    if args.command == "nova-categoria":
        created = system.create_category(args.nome, args.descricao)
        print(f"Categoria criada com ID {created}")
    elif args.command == "novo-local":
        created = system.create_location(args.nome, args.descricao)
        print(f"Local criado com ID {created}")
    elif args.command == "novo-destino":
        created = system.create_destination(args.nome, args.descricao)
        print(f"Destino criado com ID {created}")
    elif args.command == "novo-insumo":
        created = system.create_item(args.nome, args.unidade, args.categoria_id, args.estoque_minimo)
        print(f"Insumo criado com ID {created}")
    elif args.command == "entrada":
        created = system.add_stock(
            item_id=args.item_id,
            location_id=args.local_id,
            quantity=args.quantidade,
            lot_code=args.lote,
            supplier=args.fornecedor,
            unit_cost=args.custo_unitario,
            notes=args.observacao,
        )
        print(f"Entrada registrada no lote {created}")
    elif args.command == "saida":
        movement = system.remove_stock_lifo(
            item_id=args.item_id,
            quantity=args.quantidade,
            destination_id=args.destino_id,
            location_id=args.local_id,
            notes=args.observacao,
        )
        print(f"Saída registrada no movimento {movement}")
    elif args.command == "estoque":
        for row in system.current_stock():
            print(
                f"Item {row['item_id']} - {row['item']} | Categoria: {row['category']} | "
                f"Local: {row['location'] or '-'} | Quantidade: {row['quantity']} {row['unit']}"
            )
    elif args.command == "movimentos":
        for row in system.movement_history():
            print(
                f"#{row['id']} {row['movement_type']} | Item: {row['item']} | "
                f"Qtd: {row['quantity']} | Local: {row['location'] or '-'} | "
                f"Destino: {row['destination'] or '-'} | Data: {row['movement_at']}"
            )


if __name__ == "__main__":
    main()
