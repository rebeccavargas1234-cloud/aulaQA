import pytest
from app import create_app


@pytest.fixture
def app():
    return create_app({"TESTING": True, "SECRET_KEY": "test-only-key"})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def post(client):
    """Usa o token CSRF real, como um formulário do navegador."""
    client.get("/")
    with client.session_transaction() as session:
        token = session["csrf_token"]

    def send(path, **data):
        return client.post(path, data={"csrf_token": token, **data}, follow_redirects=True)
    return send
