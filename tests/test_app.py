import pytest


def test_catalog(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Ração natural para cães" in response.text
    assert "R$ 89,90" in response.text
    assert response.text.count("Adicionar ao carrinho +") == 6


def test_search_and_category(client):
    response = client.get("/", query_string={"q": "RAÇÃO", "category": "Alimentação"})
    assert response.text.count("Adicionar ao carrinho +") == 2
    assert "Bolinha interativa" not in response.text


def test_empty_search_and_escaping(client):
    response = client.get("/", query_string={"q": "<script>alert(1)</script>"})
    assert "Nenhum produto encontrado" in response.text
    assert "<script>" not in response.text


def test_empty_cart(client):
    assert "Seu carrinho está vazio" in client.get("/carrinho").text


def test_add_accumulates_and_total(client, post):
    post("/carrinho/adicionar/1", quantity="2")
    response = post("/carrinho/adicionar/1")
    assert "R$ 269,70" in response.text
    with client.session_transaction() as session:
        assert session["cart"] == {"1": 3}


def test_multiple_products_and_update(client, post):
    post("/carrinho/adicionar/1")
    post("/carrinho/adicionar/3", quantity="2")
    assert "R$ 139,70" in client.get("/carrinho").text
    response = post("/carrinho/atualizar/1", quantity="3")
    assert "R$ 319,50" in response.text


def test_remove(client, post):
    post("/carrinho/adicionar/1")
    assert "Seu carrinho está vazio" in post("/carrinho/remover/1").text


@pytest.mark.parametrize("quantity", ["0", "-1", "100", "abc", "1.5", ""])
@pytest.mark.parametrize("action", ["adicionar", "atualizar"])
def test_invalid_quantity_keeps_cart(client, post, quantity, action):
    post("/carrinho/adicionar/1", quantity="2")
    assert post(f"/carrinho/{action}/1", quantity=quantity).status_code == 400
    with client.session_transaction() as session:
        assert session["cart"] == {"1": 2}


def test_quantity_limit(client, post):
    assert post("/carrinho/adicionar/1", quantity="99").status_code == 200
    assert post("/carrinho/adicionar/1").status_code == 400
    with client.session_transaction() as session:
        assert session["cart"] == {"1": 99}


@pytest.mark.parametrize("action", ["adicionar", "atualizar", "remover"])
def test_unknown_product(post, action):
    assert post(f"/carrinho/{action}/999").status_code == 404


def test_update_absent_product(post):
    assert post("/carrinho/atualizar/1", quantity="2").status_code == 404


def test_checkout_clears_cart(client, post):
    post("/carrinho/adicionar/1", quantity="2")
    post("/carrinho/adicionar/3")
    response = post("/checkout")
    assert "COMPRA SIMULADA CONCLUÍDA" in response.text
    assert "R$ 204,70" in response.text
    assert "Seu carrinho está vazio" in client.get("/carrinho").text
    assert "Adicione produtos antes de finalizar" in post("/checkout").text


def test_empty_checkout(post):
    assert "Adicione produtos antes de finalizar" in post("/checkout").text


def test_sessions_are_isolated(app, client, post):
    post("/carrinho/adicionar/1")
    assert "Seu carrinho está vazio" in app.test_client().get("/carrinho").text
    assert "R$ 89,90" in client.get("/carrinho").text


def test_csrf_required(client):
    assert client.post("/carrinho/adicionar/1").status_code == 400
    client.get("/")
    assert client.post("/checkout", data={"csrf_token": "wrong"}).status_code == 400
    assert client.post("/checkout", data={"csrf_token": "inválido🐾"}).status_code == 400


@pytest.mark.parametrize("path", ["/checkout", "/carrinho/adicionar/1", "/carrinho/remover/1", "/carrinho/atualizar/1"])
def test_get_cannot_change_cart(client, path):
    assert client.get(path).status_code == 405


def test_health_and_not_found(client):
    assert client.get("/health").json == {"status": "ok"}
    assert client.get("/nao-existe").status_code == 404


def test_money_format(app):
    assert app.jinja_env.filters["brl"](123456) == "R$ 1.234,56"


def test_secure_cookie_in_render(monkeypatch):
    from app import create_app
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("SECRET_KEY", "deployment-test-key")
    app = create_app()
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SECRET_KEY"] == "deployment-test-key"
