"""Ad approve karna aur (agar configure ho) Facebook Page par post karna."""
from datetime import datetime, timedelta

from flask import current_app, url_for

from app import db
from app.services.facebook import post_ad_to_facebook


def facebook_configured():
    cfg = current_app.config
    return bool(cfg.get("FB_PAGE_ID") and cfg.get("FB_PAGE_ACCESS_TOKEN"))


def _absolute(endpoint, **values):
    base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    if base:
        return base + url_for(endpoint, **values)
    return url_for(endpoint, _external=True, **values)


def public_image_url(ad):
    """Facebook ko photo ka public URL chahiye; localhost par yeh None hoga."""
    if not (current_app.config.get("PUBLIC_BASE_URL") and ad.images):
        return None
    primary = next((i for i in ad.images if i.is_primary), ad.images[0])
    return _absolute("static", filename=primary.file_path)


def post_to_facebook(ad):
    if not facebook_configured():
        return None
    return post_ad_to_facebook(ad, _absolute("ads.detail", ad_id=ad.id), public_image_url(ad))


def approve_ad(ad):
    ad.status = "active"
    ad.expires_at = datetime.utcnow() + timedelta(days=30)
    db.session.commit()
    return post_to_facebook(ad)
