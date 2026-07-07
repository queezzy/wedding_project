import uuid
from datetime import datetime, timezone
from extensions import db


class Invitee(db.Model):
    """Invité pré-enregistré par l'admin avec son code d'accès personnel."""

    __tablename__ = "invitees"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    has_partner = db.Column(db.Boolean, default=False, nullable=False)
    partner_first_name = db.Column(db.String(100), nullable=True)
    partner_last_name = db.Column(db.String(100), nullable=True)
    # Nombre maximum d'enfants que cet invité peut amener
    max_children = db.Column(db.Integer, default=0, nullable=False)

    rsvp = db.relationship(
        "RSVPResponse", backref="invitee", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def partner_full_name(self):
        if self.has_partner and self.partner_first_name:
            return f"{self.partner_first_name} {self.partner_last_name or ''}".strip()
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "has_partner": self.has_partner,
            "partner_first_name": self.partner_first_name,
            "partner_last_name": self.partner_last_name,
            "max_children": self.max_children,
        }


class RSVPResponse(db.Model):
    """Réponse RSVP d'un invité (un enregistrement par foyer)."""

    __tablename__ = "rsvp_responses"

    id = db.Column(db.Integer, primary_key=True)
    invitee_id = db.Column(
        db.Integer, db.ForeignKey("invitees.id"), unique=True, nullable=False
    )
    edit_token = db.Column(
        db.String(36), unique=True, nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    # Invité principal
    principal_attending = db.Column(db.Boolean, nullable=False, default=True)
    principal_menu = db.Column(db.String(255), nullable=True)
    principal_allergies = db.Column(db.String(500), nullable=True)

    # Partenaire (null si l'invité n'a pas de partenaire)
    partner_attending = db.Column(db.Boolean, nullable=True)
    partner_menu = db.Column(db.String(255), nullable=True)
    partner_allergies = db.Column(db.String(500), nullable=True)

    # Enfants — nombre uniquement, pas de noms
    children_attending_count = db.Column(db.Integer, default=0, nullable=False)
    children_ages = db.Column(db.String(300), nullable=True)   # Ex : "4 ans, 7 ans"
    children_menu = db.Column(db.String(255), nullable=True)
    children_allergies = db.Column(db.String(500), nullable=True)

    # Informations communes
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

    def to_dict(self):
        return {
            "id": self.id,
            "edit_token": self.edit_token,
            "principal_attending": self.principal_attending,
            "principal_menu": self.principal_menu,
            "principal_allergies": self.principal_allergies,
            "partner_attending": self.partner_attending,
            "partner_menu": self.partner_menu,
            "partner_allergies": self.partner_allergies,
            "children_attending_count": self.children_attending_count,
            "children_ages": self.children_ages,
            "children_menu": self.children_menu,
            "children_allergies": self.children_allergies,
            "email_contact": self.email_contact,
            "song_suggestion": self.song_suggestion,
            "message": self.message,
            "need_accommodation": self.need_accommodation,
            "submitted_at": self.submitted_at.isoformat(),
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
