from estoquesistema import InventorySystem


def test_fluxo_completo_e_saida_lifo(tmp_path):
    db_file = tmp_path / "estoque.db"
    system = InventorySystem(db_file)

    categoria_id = system.create_category("Resina", "Matéria-prima")
    local_id = system.create_location("Galpão A")
    destino_id = system.create_destination("Produção Linha 1")
    item_id = system.create_item("Resina PP", "kg", categoria_id, min_stock=50)

    system.add_stock(item_id, local_id, 100, lot_code="L1", received_at="2025-01-01T08:00:00")
    system.add_stock(item_id, local_id, 40, lot_code="L2", received_at="2025-01-10T08:00:00")

    movement_id = system.remove_stock_lifo(item_id, 60, destino_id, location_id=local_id)

    assert movement_id > 0

    estoque = system.current_stock()
    total = sum(float(row["quantity"]) for row in estoque)
    assert total == 80

    historico = system.movement_history()
    saidas = [m for m in historico if m["movement_type"] == "OUT"]
    assert len(saidas) == 1
    assert saidas[0]["destination"] == "Produção Linha 1"


def test_nao_permita_retirada_maior_que_estoque(tmp_path):
    db_file = tmp_path / "estoque.db"
    system = InventorySystem(db_file)

    categoria_id = system.create_category("Parafuso")
    local_id = system.create_location("Prateleira B")
    destino_id = system.create_destination("Manutenção")
    item_id = system.create_item("Parafuso M8", "un", categoria_id)

    system.add_stock(item_id, local_id, 10)

    try:
        system.remove_stock_lifo(item_id, 11, destino_id)
        assert False, "Era esperado erro por estoque insuficiente"
    except ValueError as exc:
        assert "Estoque insuficiente" in str(exc)
