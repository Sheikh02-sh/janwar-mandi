from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(80))
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)  # phone OTP verified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ads = db.relationship("Ad", backref="seller", lazy="dynamic")
    favorites = db.relationship("Favorite", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Category(db.Model):
    """Bakra, Gaye, Bhains, Oont, Bheir, Murghi, etc."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)

    ads = db.relationship("Ad", backref="category", lazy="dynamic")


class Ad(db.Model):
    __tablename__ = "ads"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    breed = db.Column(db.String(80))
    gender = db.Column(db.String(10))          # male / female
    age_months = db.Column(db.Integer)
    weight_kg = db.Column(db.Float)
    price = db.Column(db.Integer, nullable=False)   # PKR
    is_negotiable = db.Column(db.Boolean, default=True)

    city = db.Column(db.String(80), nullable=False, index=True)
    area = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))

    # pending -> active -> sold / expired / rejected
    status = db.Column(db.String(20), default="pending", index=True)
    is_featured = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime)

    images = db.relationship("AdImage", backref="ad", cascade="all, delete-orphan")
    fb_post = db.relationship("FacebookPost", backref="ad", uselist=False,
                              cascade="all, delete-orphan")


class AdImage(db.Model):
    __tablename__ = "ad_images"

    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "ad_id"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    """In-app chat between buyer and seller (optional for MVP)."""
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FacebookPost(db.Model):
    """Tracks every ad that is auto-posted to the Facebook Page."""
    __tablename__ = "facebook_posts"

    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), unique=True, nullable=False)
    fb_post_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default="queued")  # queued / posted / failed
    error_message = db.Column(db.Text)
    attempts = db.Column(db.Integer, default=0)
    posted_at = db.Column(db.DateTime)
