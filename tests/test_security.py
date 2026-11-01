VEHICLE = {"make": "Demo", "model": "Hatch", "year": 2020, "fuel_type": "flex"}


def test_write_from_another_site_is_blocked(client):
    resp = client.post("/api/simulator/reset", headers={"Origin": "http://site-malicioso.example"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "FORBIDDEN"
    resp = client.post("/api/vehicles", json=VEHICLE, headers={"Origin": "http://site-malicioso.example"})
    assert resp.status_code == 403
    assert client.get("/api/vehicles").get_json()["vehicles"] == []


def test_write_from_own_pages_is_allowed(client):
    # o test client usa http://localhost como endereço do servidor
    resp = client.post("/api/vehicles", json=VEHICLE, headers={"Origin": "http://localhost"})
    assert resp.status_code == 201


def test_reads_are_not_affected_by_origin(client):
    assert client.get("/api/health", headers={"Origin": "http://outro.example"}).status_code == 200


def test_oversized_body_is_rejected(client):
    resp = client.post("/api/vehicles", data="x" * (65 * 1024), content_type="application/json")
    assert resp.status_code == 413


def test_security_headers(client):
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_errors_never_expose_stack_traces(client, monkeypatch):
    from app.services import vehicles

    def boom(*args, **kwargs):
        raise RuntimeError("detalhe interno secreto")

    monkeypatch.setattr(vehicles, "list_vehicles", boom)
    resp = client.get("/api/vehicles")
    assert resp.status_code == 500
    body = resp.get_data(as_text=True)
    assert "detalhe interno secreto" not in body and "Traceback" not in body
    assert resp.get_json()["error"]["message"] == "Erro interno no servidor. Tente novamente."


def test_text_is_stored_as_text_not_html(client):
    # validação + escape: um nome com HTML aparece escapado nas páginas
    client.post("/api/vehicles", json={**VEHICLE, "make": "<script>alert(1)</script>"})
    html = client.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
