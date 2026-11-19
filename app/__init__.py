import os

import click
from flask import Flask, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please login first."

CATEGORIES = [
    ("Bakra / Bakri (Goat)", "goat"),
    ("Gaye / Bachra (Cow)", "cow"),
    ("Bhains (Buffalo)", "buffalo"),
    ("Oont (Camel)", "camel"),
    ("Bheir / Dumba (Sheep)", "sheep"),
    ("Murghi (Poultry)", "poultry"),
    ("Ghora (Horse)", "horse"),
    ("Other", "other"),
]


def seed_categories():
    from app.models import Category

    for name, slug in CATEGORIES:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug))
    db.session.commit()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Render proxy ke peeche HTTPS/host sahi pehchanne ke liye.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    from app import models  # noqa: F401
    from app.routes.auth import bp as auth_bp
    from app.routes.ads import bp as ads_bp
    from app.routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ads_bp)
    app.register_blueprint(admin_bp)

    # ---- PWA ----
    # Service worker ka scope poori site (/) honi chahiye, is liye /static/ ki jagah root se serve karte hain.
    @app.get("/sw.js")
    def service_worker():
        resp = send_from_directory(
            os.path.join(app.static_folder, "pwa"), "sw.js",
            mimetype="application/javascript",
        )
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Service-Worker-Allowed"] = "/"
        return resp

    @app.get("/manifest.webmanifest")
    def web_manifest():
        resp = send_from_directory(
            os.path.join(app.static_folder, "pwa"), "manifest.webmanifest",
            mimetype="application/manifest+json",
        )
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    @app.template_filter("pkr")
    def pkr(value):
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return value

    @app.template_filter("age_text")
    def age_text(months):
        if not months:
            return ""
        years, rem = divmod(int(months), 12)
        parts = []
        if years:
            parts.append(f"{years} yr")
        if rem:
            parts.append(f"{rem} mo")
        return " ".join(parts)

    @app.template_filter("wa_phone")
    def wa_phone(phone):
        phone = phone or ""
        return "92" + phone[1:] if phone.startswith("0") else phone

    @app.context_processor
    def inject_globals():
        return {"nav_categories": models.Category.query.order_by(models.Category.id).all()}

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="You are not allowed to open this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404

    with app.app_context():
        db.create_all()
        seed_categories()

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--phone", prompt=True, help="03XXXXXXXXX")
    @click.password_option()
    def create_admin(name, phone, password):
        """Admin user banayein (ya existing user ko admin banayein)."""
        from app.routes.auth import normalize_phone

        normalized = normalize_phone(phone)
        if not normalized:
            click.echo("Invalid phone number. Format: 03XXXXXXXXX")
            return
        user = models.User.query.filter_by(phone=normalized).first()
        if not user:
            user = models.User(name=name, phone=normalized)
            db.session.add(user)
        user.set_password(password)
        user.is_admin = True
        user.is_verified = True
        db.session.commit()
        click.echo(f"Admin ready: {normalized}")

    return app