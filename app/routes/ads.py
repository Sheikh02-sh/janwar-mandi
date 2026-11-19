import os
import uuid

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, jsonify, current_app)
from flask_login import login_required, current_user
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import or_

from app import db
from app.models import Ad, AdImage, Category, Favorite
from app.routes.auth import normalize_phone
from app.services.publish import approve_ad

bp = Blueprint("ads", __name__)

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGES = 5


def save_image(file_storage):
    name = file_storage.filename or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise ValueError("Only JPG, PNG or WEBP images are allowed.")
    try:
        img = ImageOps.exif_transpose(Image.open(file_storage.stream)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise ValueError("One of the files is not a valid image.")
    img.thumbnail((1200, 1200))
    filename = f"{uuid.uuid4().hex}.jpg"
    img.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename), "JPEG", quality=85)
    return f"uploads/{filename}"


def delete_image_file(rel_path):
    try:
        os.remove(os.path.join(current_app.static_folder, rel_path))
    except OSError:
        pass


def favorite_ids():
    if not current_user.is_authenticated:
        return set()
    return {f.ad_id for f in Favorite.query.filter_by(user_id=current_user.id).all()}


@bp.route("/")
def index():
    query = Ad.query.filter_by(status="active")
    f = {
        "q": request.args.get("q", "").strip(),
        "category": request.args.get("category", "").strip(),
        "city": request.args.get("city", "").strip(),
        "min_price": request.args.get("min_price", type=int),
        "max_price": request.args.get("max_price", type=int),
        "sort": request.args.get("sort", "new"),
    }
    if f["q"]:
        like = f"%{f['q']}%"
        query = query.filter(or_(Ad.title.ilike(like), Ad.breed.ilike(like), Ad.description.ilike(like)))
    if f["category"]:
        query = query.join(Category).filter(Category.slug == f["category"])
    if f["city"]:
        query = query.filter(Ad.city.ilike(f"%{f['city']}%"))
    if f["min_price"] is not None:
        query = query.filter(Ad.price >= f["min_price"])
    if f["max_price"] is not None:
        query = query.filter(Ad.price <= f["max_price"])

    order = {"price_low": Ad.price.asc(), "price_high": Ad.price.desc()}.get(f["sort"], Ad.created_at.desc())
    query = query.order_by(Ad.is_featured.desc(), order)

    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    cities = [c[0] for c in db.session.query(Ad.city).filter_by(status="active").distinct().all()]
    args = {k: v for k, v in request.args.items() if k != "page"}
    return render_template("index.html", pagination=pagination, f=f, cities=cities,
                           fav_ids=favorite_ids(), args=args)


@bp.route("/ad/<int:ad_id>")
def detail(ad_id):
    ad = db.get_or_404(Ad, ad_id)
    is_owner = current_user.is_authenticated and current_user.id == ad.seller_id
    is_admin = current_user.is_authenticated and current_user.is_admin
    if ad.status not in ("active", "sold") and not (is_owner or is_admin):
        abort(404)
    if ad.status == "active" and not is_owner:
        ad.views = (ad.views or 0) + 1
        db.session.commit()
    related = (Ad.query.filter(Ad.category_id == ad.category_id, Ad.id != ad.id, Ad.status == "active")
               .order_by(Ad.created_at.desc()).limit(4).all())
    return render_template("ad_detail.html", ad=ad, is_owner=is_owner, is_admin=is_admin,
                           related=related, fav_ids=favorite_ids())


@bp.route("/ad/new", methods=["GET", "POST"])
@login_required
def create():
    categories = Category.query.order_by(Category.id).all()
    form = {"city": current_user.city or "", "contact_phone": current_user.phone}
    if request.method == "POST":
        form = request.form.to_dict()
        files = [f for f in request.files.getlist("images") if f and f.filename]
        error = None
        try:
            price = int(form.get("price", ""))
        except ValueError:
            price = None
        category = db.session.get(Category, int(form["category_id"])) if form.get("category_id", "").isdigit() else None
        phone = normalize_phone(form.get("contact_phone") or current_user.phone)

        if not category:
            error = "Please choose an animal type."
        elif len(form.get("title", "").strip()) < 5:
            error = "Title is too short."
        elif price is None or price <= 0:
            error = "Enter a valid price in PKR."
        elif not form.get("city", "").strip():
            error = "Please enter your city."
        elif not phone:
            error = "Enter a valid contact number (03XXXXXXXXX)."
        elif not files:
            error = "Please add at least one photo."
        elif len(files) > MAX_IMAGES:
            error = f"You can upload at most {MAX_IMAGES} photos."

        saved = []
        if not error:
            try:
                saved = [save_image(f) for f in files]
            except ValueError as exc:
                error = str(exc)

        if error:
            flash(error, "error")
            return render_template("ad_form.html", categories=categories, form=form)

        def to_int(key):
            v = form.get(key, "").strip()
            return int(v) if v.isdigit() else None

        def to_float(key):
            try:
                return float(form.get(key, ""))
            except ValueError:
                return None

        ad = Ad(
            seller_id=current_user.id, category_id=category.id,
            title=form["title"].strip(), description=form.get("description", "").strip(),
            breed=form.get("breed", "").strip(), gender=form.get("gender") or None,
            age_months=to_int("age_months"), weight_kg=to_float("weight_kg"),
            price=price, is_negotiable=bool(form.get("is_negotiable")),
            city=form["city"].strip(), area=form.get("area", "").strip(),
            contact_phone=phone, status="pending",
        )
        for i, path in enumerate(saved):
            ad.images.append(AdImage(file_path=path, is_primary=(i == 0)))
        db.session.add(ad)
        db.session.commit()

        if current_user.is_admin:
            approve_ad(ad)
            flash("Your ad is live.", "success")
        else:
            flash("Ad submitted. It will go live after admin approval.", "success")
        return redirect(url_for("ads.detail", ad_id=ad.id))
    return render_template("ad_form.html", categories=categories, form=form)


def owner_ad_or_404(ad_id):
    ad = db.get_or_404(Ad, ad_id)
    if ad.seller_id != current_user.id and not current_user.is_admin:
        abort(403)
    return ad


@bp.route("/ad/<int:ad_id>/sold", methods=["POST"])
@login_required
def mark_sold(ad_id):
    ad = owner_ad_or_404(ad_id)
    ad.status = "sold"
    db.session.commit()
    flash("Ad marked as sold.", "success")
    return redirect(url_for("ads.my_ads"))


@bp.route("/ad/<int:ad_id>/delete", methods=["POST"])
@login_required
def delete(ad_id):
    ad = owner_ad_or_404(ad_id)
    for img in ad.images:
        delete_image_file(img.file_path)
    Favorite.query.filter_by(ad_id=ad.id).delete()
    db.session.delete(ad)
    db.session.commit()
    flash("Ad deleted.", "success")
    return redirect(url_for("ads.my_ads"))


@bp.route("/ad/<int:ad_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(ad_id):
    db.get_or_404(Ad, ad_id)
    fav = Favorite.query.filter_by(user_id=current_user.id, ad_id=ad_id).first()
    if fav:
        db.session.delete(fav)
        saved = False
    else:
        db.session.add(Favorite(user_id=current_user.id, ad_id=ad_id))
        saved = True
    db.session.commit()
    return jsonify(saved=saved)


@bp.route("/my-ads")
@login_required
def my_ads():
    ads = Ad.query.filter_by(seller_id=current_user.id).order_by(Ad.created_at.desc()).all()
    return render_template("my_ads.html", ads=ads)


@bp.route("/favorites")
@login_required
def favorites():
    ads = (Ad.query.join(Favorite, Favorite.ad_id == Ad.id)
           .filter(Favorite.user_id == current_user.id, Ad.status.in_(["active", "sold"]))
           .order_by(Favorite.created_at.desc()).all())
    return render_template("favorites.html", ads=ads, fav_ids={a.id for a in ads})
