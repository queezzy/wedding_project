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
from models import Invitee, RSVPResponse, GuestbookEntry

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

    _admin_pw = app.config.get("ADMIN_PASSWORD", "")
    app.config["ADMIN_PASSWORD_HASH"] = (
        generate_password_hash(_admin_pw) if _admin_pw else ""
    )

    _register_routes(app)
    return app


# ---------------------------------------------------------------------------
# Auth decorators & helpers
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


def _current_invitee():
    """Retourne l'invité connecté depuis la session, ou None."""
    invitee_id = session.get("invitee_id")
    if not invitee_id:
        return None
    return db.session.get(Invitee, invitee_id)


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
        invitee = Invitee.query.filter_by(code=entered).first()
        if invitee:
            session.permanent = True
            session["site_access"] = True
            session["invitee_id"] = invitee.id
            return redirect(url_for("index"))
        flash("Code incorrect, veuillez réessayer.", "error")
        return redirect(url_for("password_gate"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("password_gate"))

    # ---- Main page ------------------------------------------------------ #

    @app.route("/")
    @_require_site_access
    def index():
        invitee = _current_invitee()
        rsvp = invitee.rsvp if invitee else None
        guestbook_entries = []
        if app.config.get("GUESTBOOK_ENABLED"):
            guestbook_entries = (
                GuestbookEntry.query.filter_by(approved=True)
                .order_by(GuestbookEntry.created_at.desc())
                .all()
            )
        return render_template(
            "index.html",
            invitee=invitee,
            rsvp=rsvp,
            guestbook_enabled=app.config.get("GUESTBOOK_ENABLED", False),
            guestbook_entries=guestbook_entries,
        )

    # ---- RSVP ----------------------------------------------------------- #

    @app.route("/api/rsvp", methods=["POST"])
    @_require_site_access
    def submit_rsvp():
        invitee = _current_invitee()
        if not invitee:
            return jsonify({"error": "Session invalide."}), 401
        if RSVPResponse.query.filter_by(invitee_id=invitee.id).first():
            return jsonify({"error": "Une réponse existe déjà. Utilisez votre lien de modification."}), 409

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Données manquantes."}), 400

        children_count = int(data.get("children_attending_count", 0) or 0)
        if children_count < 0 or children_count > invitee.max_children:
            return jsonify({"error": f"Nombre d'enfants invalide (max {invitee.max_children})."}), 400

        rsvp = RSVPResponse(
            invitee_id=invitee.id,
            principal_attending=bool(data.get("principal_attending", True)),
            principal_menu=data.get("principal_menu", "").strip() or None,
            principal_allergies=data.get("principal_allergies", "").strip() or None,
            partner_attending=bool(data.get("partner_attending")) if invitee.has_partner else None,
            partner_menu=data.get("partner_menu", "").strip() or None if invitee.has_partner else None,
            partner_allergies=data.get("partner_allergies", "").strip() or None if invitee.has_partner else None,
            children_attending_count=children_count,
            children_menu=data.get("children_menu", "").strip() or None,
            children_allergies=data.get("children_allergies", "").strip() or None,
            email_contact=data.get("email_contact", "").strip() or None,
            song_suggestion=data.get("song_suggestion", "").strip() or None,
            message=data.get("message", "").strip() or None,
            need_accommodation=bool(data.get("need_accommodation", False)),
        )
        db.session.add(rsvp)
        db.session.commit()
        return jsonify({"edit_token": rsvp.edit_token}), 201

    @app.route("/rsvp/edit/<token>", methods=["GET"])
    @_require_site_access
    def rsvp_edit_get(token):
        invitee = _current_invitee()
        rsvp = RSVPResponse.query.filter_by(edit_token=token).first_or_404()
        if not invitee or rsvp.invitee_id != invitee.id:
            abort(403)
        return jsonify({**rsvp.to_dict(), "invitee": invitee.to_dict()})

    @app.route("/rsvp/edit/<token>", methods=["POST"])
    @_require_site_access
    def rsvp_edit_post(token):
        invitee = _current_invitee()
        rsvp = RSVPResponse.query.filter_by(edit_token=token).first_or_404()
        if not invitee or rsvp.invitee_id != invitee.id:
            abort(403)

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Données manquantes."}), 400

        children_count = int(data.get("children_attending_count", 0) or 0)
        if children_count < 0 or children_count > invitee.max_children:
            return jsonify({"error": f"Nombre d'enfants invalide (max {invitee.max_children})."}), 400

        rsvp.principal_attending = bool(data.get("principal_attending", True))
        rsvp.principal_menu = data.get("principal_menu", "").strip() or None
        rsvp.principal_allergies = data.get("principal_allergies", "").strip() or None
        if invitee.has_partner:
            rsvp.partner_attending = bool(data.get("partner_attending"))
            rsvp.partner_menu = data.get("partner_menu", "").strip() or None
            rsvp.partner_allergies = data.get("partner_allergies", "").strip() or None
        rsvp.children_attending_count = children_count
        rsvp.children_menu = data.get("children_menu", "").strip() or None
        rsvp.children_allergies = data.get("children_allergies", "").strip() or None
        rsvp.email_contact = data.get("email_contact", "").strip() or None
        rsvp.song_suggestion = data.get("song_suggestion", "").strip() or None
        rsvp.message = data.get("message", "").strip() or None
        rsvp.need_accommodation = bool(data.get("need_accommodation", False))
        rsvp.updated_at = datetime.now(timezone.utc)

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
        invitees = Invitee.query.order_by(Invitee.last_name, Invitee.first_name).all()
        rsvps_submitted = sum(1 for i in invitees if i.rsvp)
        total_attending = sum(
            (1 if i.rsvp and i.rsvp.principal_attending else 0)
            + (1 if i.rsvp and i.has_partner and i.rsvp.partner_attending else 0)
            + (i.rsvp.children_attending_count if i.rsvp else 0)
            for i in invitees
        )
        pending_entries = []
        if app.config.get("GUESTBOOK_ENABLED"):
            pending_entries = GuestbookEntry.query.filter_by(approved=False).all()

        return render_template(
            "admin_dashboard.html",
            invitees=invitees,
            total_invited=len(invitees),
            rsvps_submitted=rsvps_submitted,
            total_attending=total_attending,
            guestbook_enabled=app.config.get("GUESTBOOK_ENABLED", False),
            pending_entries=pending_entries,
        )

    @app.route("/admin/invitees/add", methods=["POST"])
    @_require_admin
    def admin_add_invitee():
        code = request.form.get("code", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        has_partner = request.form.get("has_partner") == "on"
        partner_first = request.form.get("partner_first_name", "").strip() or None
        partner_last = request.form.get("partner_last_name", "").strip() or None
        max_children = int(request.form.get("max_children", 0) or 0)

        if not code or not first_name or not last_name:
            flash("Code, prénom et nom sont obligatoires.", "error")
            return redirect(url_for("admin_dashboard"))
        if Invitee.query.filter_by(code=code).first():
            flash(f"Le code « {code} » est déjà utilisé.", "error")
            return redirect(url_for("admin_dashboard"))

        invitee = Invitee(
            code=code,
            first_name=first_name,
            last_name=last_name,
            has_partner=has_partner,
            partner_first_name=partner_first if has_partner else None,
            partner_last_name=partner_last if has_partner else None,
            max_children=max(0, max_children),
        )
        db.session.add(invitee)
        db.session.commit()
        flash(f"Invité {first_name} {last_name} ajouté avec succès.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/invitees/<int:invitee_id>/delete", methods=["POST"])
    @_require_admin
    def admin_delete_invitee(invitee_id):
        invitee = db.session.get(Invitee, invitee_id) or abort(404)
        name = invitee.full_name
        db.session.delete(invitee)
        db.session.commit()
        flash(f"Invité {name} supprimé.", "success")
        return redirect(url_for("admin_dashboard"))

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
            "id", "code", "nom", "prénom",
            "a_conjoint", "nom_conjoint", "prénom_conjoint", "nb_enfants_max",
            "rsvp_envoyé",
            "invité_présent", "menu_invité", "allergies_invité",
            "conjoint_présent", "menu_conjoint", "allergies_conjoint",
            "nb_enfants_présents", "menu_enfants", "allergies_enfants",
            "hébergement", "chanson", "message", "email", "date_réponse",
        ])
        invitees = Invitee.query.order_by(Invitee.last_name).all()
        for inv in invitees:
            r = inv.rsvp
            writer.writerow([
                inv.id, inv.code, inv.last_name, inv.first_name,
                "Oui" if inv.has_partner else "Non",
                inv.partner_last_name or "", inv.partner_first_name or "",
                inv.max_children,
                "Oui" if r else "Non",
                ("Oui" if r.principal_attending else "Non") if r else "",
                r.principal_menu or "" if r else "",
                r.principal_allergies or "" if r else "",
                ("Oui" if r.partner_attending else "Non") if r and inv.has_partner else "",
                r.partner_menu or "" if r else "",
                r.partner_allergies or "" if r else "",
                r.children_attending_count if r else "",
                r.children_menu or "" if r else "",
                r.children_allergies or "" if r else "",
                ("Oui" if r.need_accommodation else "Non") if r else "",
                r.song_suggestion or "" if r else "",
                (r.message or "").replace("\n", " ") if r else "",
                r.email_contact or "" if r else "",
                r.submitted_at.strftime("%Y-%m-%d %H:%M") if r else "",
            ])

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = "attachment; filename=rsvp_export.csv"
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
