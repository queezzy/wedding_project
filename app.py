import os
import csv
import io
import uuid
from functools import wraps
from datetime import datetime, timezone

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    make_response,
    flash,
    abort,
)
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

from extensions import db, migrate
from config import config_by_name
from models import RSVPGroup, RSVPGuest, GuestbookEntry

load_dotenv()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    # Store hashed passwords to avoid plain-text comparisons at runtime
    _site_pw = app.config.get("SITE_PASSWORD", "")
    _admin_pw = app.config.get("ADMIN_PASSWORD", "")
    app.config["SITE_PASSWORD_HASH"] = (
        generate_password_hash(_site_pw) if _site_pw else ""
    )
    app.config["ADMIN_PASSWORD_HASH"] = (
        generate_password_hash(_admin_pw) if _admin_pw else ""
    )

    _register_routes(app)
    return app


# ---------------------------------------------------------------------------
# Auth decorators
# ---------------------------------------------------------------------------

def _require_site_access(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("site_access"):
            return redirect(url_for("password_gate"))
        return f(*args, **kwargs)
    return decorated


def _require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_access"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _register_routes(app: Flask) -> None:

    # ---- Password gate -------------------------------------------------- #

    @app.route("/login", methods=["GET"])
    def password_gate():
        if session.get("site_access"):
            return redirect(url_for("index"))
        return render_template("password.html")

    @app.route("/verify-password", methods=["POST"])
    def verify_password():
        entered = request.form.get("password", "").strip()
        pw_hash = app.config.get("SITE_PASSWORD_HASH", "")

        if pw_hash and check_password_hash(pw_hash, entered):
            session.permanent = True
            session["site_access"] = True
            return redirect(url_for("index"))

        flash("Code incorrect, veuillez réessayer.", "error")
        return redirect(url_for("password_gate"))

    @app.route("/logout")
    def logout():
        session.pop("site_access", None)
        return redirect(url_for("password_gate"))

    # ---- Main page ------------------------------------------------------ #

    @app.route("/")
    @_require_site_access
    def index():
        guestbook_entries = []
        if app.config.get("GUESTBOOK_ENABLED"):
            guestbook_entries = (
                GuestbookEntry.query.filter_by(approved=True)
                .order_by(GuestbookEntry.created_at.desc())
                .all()
            )
        return render_template(
            "index.html",
            guestbook_enabled=app.config.get("GUESTBOOK_ENABLED", False),
            guestbook_entries=guestbook_entries,
        )

    # ---- RSVP ----------------------------------------------------------- #

    @app.route("/api/rsvp", methods=["POST"])
    @_require_site_access
    def submit_rsvp():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Données manquantes."}), 400

        guests_data = data.get("guests", [])
        if not guests_data:
            return jsonify({"error": "Au moins une personne est requise."}), 400

        # Validate guest types
        valid_types = set(RSVPGuest.TYPES)
        for g in guests_data:
            if g.get("guest_type", "adulte") not in valid_types:
                return jsonify({"error": "Type d'invité invalide."}), 400
            if not g.get("first_name", "").strip() or not g.get("last_name", "").strip():
                return jsonify({"error": "Nom et prénom requis pour chaque personne."}), 400

        group = RSVPGroup(
            edit_token=str(uuid.uuid4()),
            email_contact=data.get("email_contact", "").strip() or None,
            song_suggestion=data.get("song_suggestion", "").strip() or None,
            message=data.get("message", "").strip() or None,
            need_accommodation=bool(data.get("need_accommodation", False)),
        )
        db.session.add(group)
        db.session.flush()  # get group.id

        for g in guests_data:
            guest = RSVPGuest(
                group_id=group.id,
                first_name=g["first_name"].strip(),
                last_name=g["last_name"].strip(),
                guest_type=g.get("guest_type", "adulte"),
                attending=bool(g.get("attending", True)),
                menu_choice=g.get("menu_choice", "").strip() or None,
                allergies=g.get("allergies", "").strip() or None,
            )
            db.session.add(guest)

        db.session.commit()
        return jsonify({"edit_token": group.edit_token}), 201

    @app.route("/rsvp/edit/<token>", methods=["GET"])
    @_require_site_access
    def rsvp_edit_get(token):
        group = RSVPGroup.query.filter_by(edit_token=token).first_or_404()
        return jsonify(group.to_dict())

    @app.route("/rsvp/edit/<token>", methods=["POST"])
    @_require_site_access
    def rsvp_edit_post(token):
        group = RSVPGroup.query.filter_by(edit_token=token).first_or_404()
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Données manquantes."}), 400

        guests_data = data.get("guests", [])
        if not guests_data:
            return jsonify({"error": "Au moins une personne est requise."}), 400

        valid_types = set(RSVPGuest.TYPES)
        for g in guests_data:
            if g.get("guest_type", "adulte") not in valid_types:
                return jsonify({"error": "Type d'invité invalide."}), 400
            if not g.get("first_name", "").strip() or not g.get("last_name", "").strip():
                return jsonify({"error": "Nom et prénom requis pour chaque personne."}), 400

        group.email_contact = data.get("email_contact", "").strip() or None
        group.song_suggestion = data.get("song_suggestion", "").strip() or None
        group.message = data.get("message", "").strip() or None
        group.need_accommodation = bool(data.get("need_accommodation", False))
        group.updated_at = datetime.now(timezone.utc)

        # Replace all guests
        RSVPGuest.query.filter_by(group_id=group.id).delete()
        for g in guests_data:
            guest = RSVPGuest(
                group_id=group.id,
                first_name=g["first_name"].strip(),
                last_name=g["last_name"].strip(),
                guest_type=g.get("guest_type", "adulte"),
                attending=bool(g.get("attending", True)),
                menu_choice=g.get("menu_choice", "").strip() or None,
                allergies=g.get("allergies", "").strip() or None,
            )
            db.session.add(guest)

        db.session.commit()
        return jsonify({"ok": True})

    # ---- Guestbook (conditionnel) --------------------------------------- #

    @app.route("/api/guestbook", methods=["POST"])
    @_require_site_access
    def submit_guestbook():
        if not app.config.get("GUESTBOOK_ENABLED"):
            abort(404)
        data = request.get_json(silent=True) or {}
        author = data.get("author_name", "").strip()
        message = data.get("message", "").strip()
        if not author or not message:
            return jsonify({"error": "Nom et message requis."}), 400
        entry = GuestbookEntry(author_name=author, message=message)
        db.session.add(entry)
        db.session.commit()
        return jsonify({"ok": True}), 201

    # ---- Admin ---------------------------------------------------------- #

    @app.route("/admin", methods=["GET"])
    def admin_login():
        if session.get("admin_access"):
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html")

    @app.route("/admin/login", methods=["POST"])
    def admin_login_post():
        entered = request.form.get("password", "").strip()
        pw_hash = app.config.get("ADMIN_PASSWORD_HASH", "")
        if pw_hash and check_password_hash(pw_hash, entered):
            session["admin_access"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Mot de passe incorrect.", "error")
        return redirect(url_for("admin_login"))

    @app.route("/admin/dashboard")
    @_require_admin
    def admin_dashboard():
        groups = (
            RSVPGroup.query.order_by(RSVPGroup.submitted_at.desc()).all()
        )
        total_attending = (
            RSVPGuest.query.filter_by(attending=True).count()
        )
        total_declined = (
            RSVPGuest.query.filter_by(attending=False).count()
        )
        # Guestbook entries pending approval
        pending_entries = []
        if app.config.get("GUESTBOOK_ENABLED"):
            pending_entries = GuestbookEntry.query.filter_by(approved=False).all()

        return render_template(
            "admin_dashboard.html",
            groups=groups,
            total_attending=total_attending,
            total_declined=total_declined,
            guestbook_enabled=app.config.get("GUESTBOOK_ENABLED", False),
            pending_entries=pending_entries,
        )

    @app.route("/admin/approve-guestbook/<int:entry_id>", methods=["POST"])
    @_require_admin
    def admin_approve_guestbook(entry_id):
        entry = GuestbookEntry.query.get_or_404(entry_id)
        entry.approved = True
        db.session.commit()
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/export.csv")
    @_require_admin
    def admin_export_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "group_id", "edit_token", "email_contact", "need_accommodation",
            "song_suggestion", "message", "submitted_at",
            "guest_first_name", "guest_last_name", "guest_type",
            "attending", "menu_choice", "allergies",
        ])
        groups = RSVPGroup.query.order_by(RSVPGroup.submitted_at).all()
        for group in groups:
            for guest in group.guests:
                writer.writerow([
                    group.id,
                    group.edit_token,
                    group.email_contact or "",
                    "Oui" if group.need_accommodation else "Non",
                    group.song_suggestion or "",
                    (group.message or "").replace("\n", " "),
                    group.submitted_at.strftime("%Y-%m-%d %H:%M"),
                    guest.first_name,
                    guest.last_name,
                    guest.guest_type,
                    "Oui" if guest.attending else "Non",
                    guest.menu_choice or "",
                    guest.allergies or "",
                ])

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = (
            "attachment; filename=rsvp_export.csv"
        )
        return response

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("admin_access", None)
        return redirect(url_for("admin_login"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    app.run()
