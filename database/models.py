from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    websites = db.relationship(
        "Website",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Website(db.Model):
    __tablename__ = "websites"

    id = db.Column(db.Integer, primary_key=True)

    website_name = db.Column(db.String(100), nullable=False)

    url = db.Column(db.String(255), nullable=False)

    monitoring_interval = db.Column(db.Integer, default=5)

    status = db.Column(db.Boolean, default=True)

    ssl_expiry = db.Column(db.DateTime)

    ssl_warning = db.Column(db.Boolean, default=False)

    last_alert_sent = db.Column(db.String(50), default="")

    last_alert_time = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

class MonitoringLog(db.Model):

    __tablename__ = "monitoring_logs"

    id = db.Column(db.Integer, primary_key=True)

    website_id = db.Column(
        db.Integer,
        db.ForeignKey("websites.id"),
        nullable=False
    )

    status_code = db.Column(db.Integer)

    response_time = db.Column(db.Float)

    is_online = db.Column(db.Boolean)

    checked_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    website = db.relationship("Website")

class Notification(db.Model):

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(db.String(255))

    message = db.Column(db.Text)

    type = db.Column(db.String(30))

    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )