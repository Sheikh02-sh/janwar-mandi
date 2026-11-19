from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.models import Ad
from app.services.publish import approve_ad, post_to_facebook, facebook_configured

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.route("/")
@admin_required
def dashboard():
    status = request.args.get("status", "pending")
    ads = Ad.query.filter_by(status=status).order_by(Ad.created_at.desc()).all()
    counts = dict(db.session.query(Ad.status, func.count(Ad.id)).group_by(Ad.status).all())
    return render_template("admin.html", ads=ads, status=status, counts=counts,
                           fb_ok=facebook_configured())


@bp.route("/ad/<int:ad_id>/approve", methods=["POST"])
@admin_required
def approve(ad_id):
    ad = db.get_or_404(Ad, ad_id)
    record = approve_ad(ad)
    if record is None:
        flash("Ad approved. (Facebook is not configured, so it was not posted.)", "success")
    elif record.status == "posted":
        flash("Ad approved and posted to the Facebook Page.", "success")
    else:
        flash("Ad approved, but Facebook posting failed. Check the error below.", "error")
        return redirect(url_for("admin.dashboard", status="active"))
    return redirect(url_for("admin.dashboard"))


@bp.route("/ad/<int:ad_id>/reject", methods=["POST"])
@admin_required
def reject(ad_id):
    ad = db.get_or_404(Ad, ad_id)
    ad.status = "rejected"
    db.session.commit()
    flash("Ad rejected.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.route("/ad/<int:ad_id>/facebook", methods=["POST"])
@admin_required
def facebook(ad_id):
    ad = db.get_or_404(Ad, ad_id)
    record = post_to_facebook(ad)
    if record is None:
        flash("Facebook is not configured in .env.", "error")
    elif record.status == "posted":
        flash("Posted to the Facebook Page.", "success")
    else:
        flash("Facebook posting failed. Check the error below.", "error")
    return redirect(url_for("admin.dashboard", status=ad.status))
