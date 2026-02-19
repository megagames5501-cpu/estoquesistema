from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import webbrowser

from .inventory import InventorySystem


CSS = """
body { font-family: Arial, sans-serif; margin: 0; background: #f4f6f8; color: #1f2937; }
header { background: #0f172a; color: white; padding: 16px 24px; }
main { padding: 20px; display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.card { background: white; border-radius: 10px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
h2 { margin-top: 0; font-size: 1.05rem; }
label { display: block; font-size: 0.9rem; margin-top: 8px; }
input, textarea { width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #cbd5e1; border-radius: 8px; }
button { margin-top: 10px; padding: 8px 12px; border: 0; border-radius: 8px; background: #2563eb; color: white; cursor: pointer; }
button:hover { background: #1d4ed8; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; border-bottom: 1px solid #e2e8f0; padding: 8px; }
.alert { margin: 12px 20px 0; padding: 10px 12px; border-radius: 8px; }
.ok { background: #dcfce7; color: #166534; }
.err { background: #fee2e2; color: #991b1b; }
"""


def _form_card(title: str, action: str, fields: list[tuple[str, str, str]]) -> str:
    inputs = []
    for label, name, placeholder in fields:
        input_type = "number" if name.endswith("_id") or name in {"quantidade", "estoque_minimo", "custo_unitario"} else "text"
        step = ' step="any"' if name in {"quantidade", "estoque_minimo", "custo_unitario"} else ""
        inputs.append(
            f"<label>{escape(label)}<input name='{escape(name)}' placeholder='{escape(placeholder)}' type='{input_type}'{step} required></label>"
        )

    return (
        f"<section class='card'><h2>{escape(title)}</h2>"
        f"<form method='post' action='/{escape(action)}'>{''.join(inputs)}"
        "<button type='submit'>Salvar</button></form></section>"
    )


def render_page(system: InventorySystem, message: str = "", error: bool = False) -> bytes:
    stock_rows = system.current_stock()
    movement_rows = system.movement_history()

    stock_table = "".join(
        "<tr>"
        f"<td>{escape(str(r['item_id']))}</td>"
        f"<td>{escape(str(r['item']))}</td>"
        f"<td>{escape(str(r['category']))}</td>"
        f"<td>{escape(str(r['location'] or '-'))}</td>"
        f"<td>{escape(str(r['quantity']))}</td>"
        f"<td>{escape(str(r['unit']))}</td>"
        "</tr>"
        for r in stock_rows
    )

    mov_table = "".join(
        "<tr>"
        f"<td>{escape(str(r['id']))}</td>"
        f"<td>{escape(str(r['movement_type']))}</td>"
        f"<td>{escape(str(r['item']))}</td>"
        f"<td>{escape(str(r['quantity']))}</td>"
        f"<td>{escape(str(r['location'] or '-'))}</td>"
        f"<td>{escape(str(r['destination'] or '-'))}</td>"
        f"<td>{escape(str(r['movement_at']))}</td>"
        "</tr>"
        for r in movement_rows[:20]
    )

    alert = ""
    if message:
        alert_class = "err" if error else "ok"
        alert = f"<div class='alert {alert_class}'>{escape(message)}</div>"

    html = f"""
    <!doctype html>
    <html lang='pt-br'>
    <head>
      <meta charset='utf-8'>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <title>Sistema de Estoque Visual</title>
      <style>{CSS}</style>
    </head>
    <body>
      <header>
        <h1>Sistema de Estoque Visual (LIFO)</h1>
        <small>Último que entra, primeiro que sai + rastreio de destino.</small>
      </header>
      {alert}
      <main>
        {_form_card('Nova categoria', 'nova-categoria', [('Nome', 'nome', 'Ex.: Resinas'), ('Descrição', 'descricao', 'Opcional')])}
        {_form_card('Novo local', 'novo-local', [('Nome', 'nome', 'Ex.: Galpão A'), ('Descrição', 'descricao', 'Opcional')])}
        {_form_card('Novo destino', 'novo-destino', [('Nome', 'nome', 'Ex.: Produção Linha 1'), ('Descrição', 'descricao', 'Opcional')])}
        {_form_card('Novo insumo', 'novo-insumo', [('Nome', 'nome', 'Ex.: Resina PP'), ('Unidade', 'unidade', 'kg'), ('ID categoria', 'categoria_id', '1'), ('Estoque mínimo', 'estoque_minimo', '0')])}
        {_form_card('Entrada de estoque', 'entrada', [('ID item', 'item_id', '1'), ('ID local', 'local_id', '1'), ('Quantidade', 'quantidade', '100'), ('Lote', 'lote', 'L1'), ('Fornecedor', 'fornecedor', 'Fornecedor X'), ('Custo unitário', 'custo_unitario', '0')])}
        {_form_card('Saída LIFO', 'saida', [('ID item', 'item_id', '1'), ('Quantidade', 'quantidade', '20'), ('ID destino', 'destino_id', '1'), ('ID local (opcional, use 0 para todos)', 'local_id', '0')])}

        <section class='card' style='grid-column: 1 / -1;'>
          <h2>Estoque atual</h2>
          <div class='table-wrap'>
            <table>
              <thead><tr><th>ID</th><th>Item</th><th>Categoria</th><th>Local</th><th>Qtd</th><th>Unid.</th></tr></thead>
              <tbody>{stock_table or '<tr><td colspan="6">Sem dados</td></tr>'}</tbody>
            </table>
          </div>
        </section>

        <section class='card' style='grid-column: 1 / -1;'>
          <h2>Últimas movimentações</h2>
          <div class='table-wrap'>
            <table>
              <thead><tr><th>ID</th><th>Tipo</th><th>Item</th><th>Qtd</th><th>Local</th><th>Destino</th><th>Data</th></tr></thead>
              <tbody>{mov_table or '<tr><td colspan="7">Sem dados</td></tr>'}</tbody>
            </table>
          </div>
        </section>
      </main>
    </body>
    </html>
    """
    return html.encode("utf-8")


class InventoryHandler(BaseHTTPRequestHandler):
    system: InventorySystem

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        message = qs.get("msg", [""])[0]
        error = qs.get("err", ["0"])[0] == "1"
        body = render_page(self.system, message=message, error=error)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8")
        form = {k: v[0] for k, v in parse_qs(raw).items()}

        try:
            if self.path == "/nova-categoria":
                self.system.create_category(form["nome"], form.get("descricao", ""))
                self._redirect("Categoria criada com sucesso")
            elif self.path == "/novo-local":
                self.system.create_location(form["nome"], form.get("descricao", ""))
                self._redirect("Local criado com sucesso")
            elif self.path == "/novo-destino":
                self.system.create_destination(form["nome"], form.get("descricao", ""))
                self._redirect("Destino criado com sucesso")
            elif self.path == "/novo-insumo":
                self.system.create_item(
                    name=form["nome"],
                    unit=form["unidade"],
                    category_id=int(form["categoria_id"]),
                    min_stock=float(form.get("estoque_minimo", "0") or 0),
                )
                self._redirect("Insumo criado com sucesso")
            elif self.path == "/entrada":
                self.system.add_stock(
                    item_id=int(form["item_id"]),
                    location_id=int(form["local_id"]),
                    quantity=float(form["quantidade"]),
                    lot_code=form.get("lote", ""),
                    supplier=form.get("fornecedor", ""),
                    unit_cost=float(form["custo_unitario"]) if form.get("custo_unitario") else None,
                )
                self._redirect("Entrada registrada com sucesso")
            elif self.path == "/saida":
                local_raw = int(form.get("local_id", "0") or 0)
                self.system.remove_stock_lifo(
                    item_id=int(form["item_id"]),
                    quantity=float(form["quantidade"]),
                    destination_id=int(form["destino_id"]),
                    location_id=local_raw if local_raw > 0 else None,
                )
                self._redirect("Saída registrada com sucesso")
            else:
                self._redirect("Ação inválida", error=True)
        except Exception as exc:
            self._redirect(str(exc), error=True)

    def _redirect(self, msg: str, error: bool = False) -> None:
        encoded = msg.replace(" ", "+")
        err = "1" if error else "0"
        self.send_response(303)
        self.send_header("Location", f"/?msg={encoded}&err={err}")
        self.end_headers()


def run_server(db_path: str = "estoque.db", host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    InventoryHandler.system = InventorySystem(Path(db_path))
    server = ThreadingHTTPServer((host, port), InventoryHandler)
    url = f"http://{host}:{port}"
    print(f"Sistema visual iniciado em: {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    server.serve_forever()


if __name__ == "__main__":
    run_server()
