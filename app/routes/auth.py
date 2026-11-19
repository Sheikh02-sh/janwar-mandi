import re

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User

bp = Blueprint("auth", __name__)


def normalize_phone(raw):
    """+92 300 1234567 / 0300-1234567 -> 03001234567. Invalid ho to None."""
    p = re.sub(r"[\s\-()]", "", raw or "")
    if p.startswith("+92"):
        p = "0" + p[3:]
    elif p.startswith("0092"):
        p = "0" + p[4:]
    elif p.startswith("92") and len(p) == 12:
        p = "0" + p[2:]
    return p if re.fullmatch(r"03\d{9}", p) else None


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("ads.index"))
    form = {}
    if request.method == "POST":
        form = request.form.to_dict()
        name = form.get("name", "").strip()
        phone = normalize_phone(form.get("phone"))
        city = form.get("city", "").strip()
        password = form.get("password", "")
        error = None
        if len(name) < 2:
            error = "Please enter your name."
        elif not phone:
            error = "Enter a valid Pakistani mobile number (03XXXXXXXXX)."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != form.get("confirm", ""):
            error = "Passwords do not match."
        elif User.query.filter_by(phone=phone).first():
            error = "This phone number is already registered."
        if error:
            flash(error, "error")
        else:
            user = User(name=name, phone=phone, city=city)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. Welcome!", "success")
            return redirect(url_for("ads.index"))
    return render_template("register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("ads.index"))
    if request.method == "POST":
        phone = normalize_phone(request.form.get("phone"))
        user = User.query.filter_by(phone=phone).first() if phone else None
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=True)
            return redirect(safe_next(request.args.get("next")) or url_for("ads.index"))
        flash("Wrong phone number or password.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("ads.index"))
