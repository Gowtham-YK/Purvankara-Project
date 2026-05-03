from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# -------------------
# USER TABLE
# -------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))  # "stp" or "demand"

# -------------------
# SUPPLY TABLE
# -------------------
class Supply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    operator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    available_volume = db.Column(db.Float)
    quality_classification = db.Column(db.String(100))
    report_filename = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------
# DEMAND REQUEST TABLE
# -------------------
class DemandRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(150))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    requested_volume = db.Column(db.Float)
    status = db.Column(db.String(50), default="Pending")