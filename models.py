import uuid
from datetime import datetime, timezone
from extensions import db


class RSVPGroup(db.Model):
    """Un foyer / groupe familial qui répond."""

    __tablename__ = "rsvp_groups"

    id = db.Column(db.Integer, primary_key=True)
    edit_token = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    email_contact = db.Column(db.String(254), nullable=True)
    song_suggestion = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=True)
    need_accommodation = db.Column(db.Boolean, default=False, nullable=False)
    submitted_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    guests = db.relationship(
        "RSVPGuest", backref="group", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "edit_token": self.edit_token,
            "email_contact": self.email_contact,
            "song_suggestion": self.song_suggestion,
            "message": self.message,
            "need_accommodation": self.need_accommodation,
            "submitted_at": self.submitted_at.isoformat(),
            "guests": [g.to_dict() for g in self.guests],
        }


class RSVPGuest(db.Model):
    """Une personne individuelle dans un groupe RSVP."""

    __tablename__ = "rsvp_guests"

    TYPES = ("adulte", "partenaire", "enfant")

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("rsvp_groups.id"), nullable=False
    )
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    guest_type = db.Column(db.String(20), nullable=False, default="adulte")
    attending = db.Column(db.Boolean, nullable=False, default=True)
    menu_choice = db.Column(db.String(255), nullable=True)
    allergies = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "guest_type": self.guest_type,
            "attending": self.attending,
            "menu_choice": self.menu_choice,
            "allergies": self.allergies,
        }


class GuestbookEntry(db.Model):
    """Livre d'or — activé après le mariage via GUESTBOOK_ENABLED."""

    __tablename__ = "guestbook_entries"

    id = db.Column(db.Integer, primary_key=True)
    author_name = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    approved = db.Column(db.Boolean, default=False, nullable=False)
