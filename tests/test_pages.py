import re

import pytest

from app.db import connect
from app.routes.pages import PAGES


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p["endpoint"])
def test_page_opens_with_layout(client, page):
    resp = client.get(page["path"])
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert f"<h1>{page['title']}</h1>" in html
    assert 'aria-current="page"' in html
    assert "ECU simulada" in html
    assert "Sem conexão com veículo real" in html
    # Toda tela aparece na navegação lateral.
    for other in PAGES:
        assert f'href="{other["path"]}"' in html


def test_no_broken_internal_links(client):
    links = set()
    for page in PAGES:
        html = client.get(page["path"]).get_data(as_text=True)
        links |= set(re.findall(r'(?:href|src)="(/[^"#]*)"', html))
    assert links, "nenhum link encontrado"
    for link in sorted(links):
        assert client.get(link).status_code == 200, link


def test_unknown_page_returns_html_404(client):
    resp = client.get("/pagina-que-nao-existe")
    assert resp.status_code == 404
    assert resp.mimetype == "text/html"
    html = resp.get_data(as_text=True)
    assert "Página não encontrada." in html
    assert 'href="/"' in html


def test_header_without_active_vehicle(client):
    html = client.get("/").get_data(as_text=True)
    assert "Nenhum veículo ativo" in html


def test_header_shows_active_vehicle(client, db_path):
    conn = connect(db_path)
    conn.execute(
        "INSERT INTO vehicles (make, model, year, engine, fuel_type, mileage_km, created_at, updated_at, is_active)"
        " VALUES ('Demo', 'Sedan Didático', 2019, '1.6', 'flex', 45210, 't', 't', 1)"
    )
    conn.commit()
    conn.close()
    html = client.get("/").get_data(as_text=True)
    assert "Demo Sedan Didático 2019" in html
    assert "45.210 km" in html
    assert "Nenhum veículo ativo" not in html


def test_pending_pages_have_no_action_buttons(client):
    # Telas ainda não implementadas não podem exibir botões sem função.
    for page in PAGES:
        if page.get("template"):  # tela já implementada
            continue
        html = client.get(page["path"]).get_data(as_text=True)
        content = html.split('<main id="conteudo"', 1)[1].split("</main>", 1)[0]
        assert "<button" not in content
        assert f"Fase {page['phase']}" in content
