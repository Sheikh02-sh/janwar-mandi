"""Facebook Page par ad auto-post karne ka service.

Zaroori: Meta developer app + Page access token
(permissions: pages_manage_posts, pages_read_engagement).
"""
import requests
from datetime import datetime
from flask import current_app

from app import db
from app.models import Ad, FacebookPost


def build_caption(ad: Ad, ad_url: str) -> str:
    return (
        f"🐐 {ad.title}\n"
        f"💰 Qeemat: Rs {ad.price:,}\n"
        f"📍 Shehar: {ad.city}\n"
        f"📞 Rabta: {ad.contact_phone or 'Ad mein dekhein'}\n\n"
        f"Poori detail yahan dekhein: {ad_url}"
    )


def post_ad_to_facebook(ad: Ad, ad_url: str, image_url: str | None = None):
    cfg = current_app.config
    record = ad.fb_post or FacebookPost(ad_id=ad.id)
    record.attempts = (record.attempts or 0) + 1
    db.session.add(record)

    base = f"https://graph.facebook.com/{cfg['FB_GRAPH_VERSION']}/{cfg['FB_PAGE_ID']}"
    caption = build_caption(ad, ad_url)

    try:
        if image_url:
            resp = requests.post(
                f"{base}/photos",
                data={"url": image_url, "caption": caption,
                      "access_token": cfg["FB_PAGE_ACCESS_TOKEN"]},
                timeout=30,
            )
        else:
            resp = requests.post(
                f"{base}/feed",
                data={"message": caption, "link": ad_url,
                      "access_token": cfg["FB_PAGE_ACCESS_TOKEN"]},
                timeout=30,
            )
        resp.raise_for_status()
        record.fb_post_id = resp.json().get("post_id") or resp.json().get("id")
        record.status = "posted"
        record.posted_at = datetime.utcnow()
        record.error_message = None
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error_message = str(exc)

    db.session.commit()
    return record
