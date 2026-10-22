"""Pet Shop didático: catálogo fixo e carrinho em sessão assinada."""
import os
import secrets

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

PRODUCTS = {
    1: dict(id=1, name="Ração natural para cães", category="Alimentação", price=8990, icon="🐕", description="Nutrição equilibrada para cães adultos. Pacote de 3 kg."),
    2: dict(id=2, name="Ração premium para gatos", category="Alimentação", price=6990, icon="🐈", description="Sabor e cuidado em cada porção. Pacote de 1 kg."),
    3: dict(id=3, name="Bolinha interativa", category="Brinquedos", price=2490, icon="🎾", description="Mais diversão e movimento na rotina do seu pet."),
    4: dict(id=4, name="Caminha aconchego", category="Acessórios", price=12990, icon="🛏️", description="Um cantinho macio para os melhores cochilos."),
    5: dict(id=5, name="Shampoo suave", category="Higiene", price=3490, icon="🫧", description="Limpeza delicada para cães e gatos. Frasco de 500 ml."),
    6: dict(id=6, name="Guia para passeios", category="Acessórios", price=4990, icon="🦮", description="Conforto para explorar o mundo ao seu lado."),
}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("RENDER") == "true",
    )
    if test_config:
        app.config.update(test_config)

    @app.template_filter("brl")
    def brl(cents):
        return f"R$ {cents // 100:,}".replace(",", ".") + f",{cents % 100:02d}"

    def cart_items():
        return [dict(product=PRODUCTS[int(pid)], quantity=qty,
                     subtotal=PRODUCTS[int(pid)]["price"] * qty)
                for pid, qty in session.get("cart", {}).items()]

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(32)
        return session["csrf_token"]

    @app.before_request
    def protect_forms():
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token", "")
            if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
                abort(400, description="Formulário expirado. Recarregue a página e tente novamente.")

    @app.context_processor
    def shared():
        return dict(cart_count=sum(session.get("cart", {}).values()), csrf_token=csrf_token)

    @app.get("/")
    def home():
        return catalog(show_hero=True)

    @app.get("/catalogo", strict_slashes=False)
    def catalog(show_hero=False):
        query = request.args.get("q", "").strip()
        category = request.args.get("category", "")
        products = [p for p in PRODUCTS.values()
                    if query.casefold() in p["name"].casefold()
                    and (not category or p["category"] == category)]
        return render_template("catalog.html", products=products, query=query,
                               category=category, show_hero=show_hero,
                               categories=sorted({p["category"] for p in PRODUCTS.values()}))

    @app.get("/carrinho")
    def cart():
        items = cart_items()
        return render_template("cart.html", items=items, total=sum(i["subtotal"] for i in items))

    def product_or_404(product_id):
        if product_id not in PRODUCTS:
            abort(404)

    def quantity():
        try:
            value = int(request.form.get("quantity", "1"))
        except ValueError:
            abort(400, description="Quantidade inválida.")
        if not 1 <= value <= 99:
            abort(400, description="Informe uma quantidade entre 1 e 99.")
        return value

    @app.post("/carrinho/adicionar/<int:product_id>")
    def add(product_id):
        product_or_404(product_id)
        qty = quantity()
        basket = session.get("cart", {}).copy()
        key = str(product_id)
        if basket.get(key, 0) + qty > 99:
            abort(400, description="Limite de 99 unidades por produto.")
        basket[key] = basket.get(key, 0) + qty
        session["cart"] = basket
        flash("Produto adicionado ao carrinho!", "success")
        return redirect(url_for("cart"))

    @app.post("/carrinho/atualizar/<int:product_id>")
    def update(product_id):
        product_or_404(product_id)
        basket = session.get("cart", {}).copy()
        if str(product_id) not in basket:
            abort(404)
        basket[str(product_id)] = quantity()
        session["cart"] = basket
        return redirect(url_for("cart"))

    @app.post("/carrinho/remover/<int:product_id>")
    def remove(product_id):
        product_or_404(product_id)
        basket = session.get("cart", {}).copy()
        basket.pop(str(product_id), None)
        session["cart"] = basket
        return redirect(url_for("cart"))

    @app.post("/checkout")
    def checkout():
        items = cart_items()
        if not items:
            flash("Adicione produtos antes de finalizar.", "error")
            return redirect(url_for("cart"))
        total = sum(i["subtotal"] for i in items)
        session.pop("cart", None)
        return render_template("checkout.html", items=items, total=total)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(400)
    @app.errorhandler(404)
    def error_page(error):
        return render_template("error.html", error=error), error.code

    return app


app = create_app()
