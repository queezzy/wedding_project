# 💛 Joyce & Franck — Site de mariage

Site web privé pour le mariage de **Joyce Maïssa & Franck Quentin**, le **19 septembre 2026** à Meaux, France.

> Documentation complète → [`docs/`](docs/)

---

## Aperçu rapide

| Élément | Valeur |
|---|---|
| URL prod | `https://<votre-domaine>` |
| Accès invités | `/login` — code d'invitation |
| Tableau de bord | `/admin` — mot de passe admin |
| Technologie | Flask 3 · Jinja2 · SQLite (dev) / PostgreSQL (prod) |
| Déploiement | Railway |

---

## Démarrage local

### Prérequis
- Python 3.12+
- pip

### 1. Cloner et créer l'environnement

```bash
git clone <repo-url>
cd proj_test
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configurer l'environnement

```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

Variables obligatoires dans `.env` :

| Variable | Exemple | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | `openssl rand -hex 32` | Clé secrète Flask (sessions) |
| `ADMIN_PASSWORD` | `admin-secret` | Mot de passe du tableau de bord |
| `DATABASE_URL` | `sqlite:///mariage_dev.db` | URL de connexion BDD |
| `FLASK_ENV` | `development` | `development` ou `production` |
| `GUESTBOOK_ENABLED` | `false` | Activer le livre d'or |

### 4. Initialiser la base de données

```bash
flask db init       # une seule fois
flask db migrate -m "initial"
flask db upgrade
```

### 5. Lancer le serveur

```bash
flask run
# → http://127.0.0.1:5000
```

---

## Déploiement Railway

1. Créer un projet Railway et ajouter un service **PostgreSQL**
2. Pousser le code — Railway détecte le `Procfile` automatiquement
3. Définir les variables d'environnement dans les **Settings > Variables** :
   ```
   FLASK_SECRET_KEY=<générer>
   ADMIN_PASSWORD=<votre mdp admin>
   DATABASE_URL=<Railway fournit cette valeur automatiquement>
   FLASK_ENV=production
   GUESTBOOK_ENABLED=false
   ```
4. Railway lance : `gunicorn app:app --workers 2 --timeout 120`

> **Note** : Le driver PostgreSQL (`psycopg2-binary`) est dans `requirements-prod.txt`. Configurer Railway pour utiliser ce fichier : variable d'env `PIP_REQUIREMENTS_FILE=requirements-prod.txt`, ou renommer `requirements-prod.txt` en `requirements.txt` avant le déploiement.

---

## Structure des fichiers

```
proj_test/
├── app.py                  ← Factory Flask + toutes les routes
├── config.py               ← DevelopmentConfig / ProductionConfig
├── extensions.py           ← SQLAlchemy + Flask-Migrate (init)
├── models.py               ← Invitee, RSVPResponse, GuestbookEntry
│
├── templates/
│   ├── base.html           ← Layout : <head>, fonts, AOS CDN
│   ├── password.html       ← Page de code d'invitation
│   ← index.html           ← Page principale one-page (toutes sections)
│   ├── admin_login.html    ← Connexion admin
│   └── admin_dashboard.html← Tableau de bord + export CSV
│
├── static/
│   ├── css/style.css       ← Palette pastel, responsive, animations
│   ├── js/main.js          ← Nav sticky, countdown, AOS, FAQ
│   ├── js/gallery.js       ← Lightbox galerie
│   └── js/rsvp.js          ← Formulaire RSVP dynamique
│
├── migrations/             ← Alembic / Flask-Migrate
├── requirements.txt        ← Dépendances dev (sans psycopg2)
├── requirements-prod.txt   ← Dépendances prod (avec psycopg2)
├── Procfile                ← Commande gunicorn pour Railway
├── runtime.txt             ← Version Python pour Railway
├── .env.example            ← Template de configuration
└── docs/                   ← Documentation complète
    ├── FUNCTIONAL.md
    ├── TECHNICAL.md
    └── DATABASE.md
```

---

## Documentation

| Document | Contenu |
|---|---|
| [docs/FUNCTIONAL.md](docs/FUNCTIONAL.md) | Fonctionnalités, parcours utilisateurs, sections de la page |
| [docs/TECHNICAL.md](docs/TECHNICAL.md) | Architecture, routes API, sécurité, déploiement |
| [docs/DATABASE.md](docs/DATABASE.md) | Schéma de base de données, diagramme ER, requêtes |

---

## Personnalisations à faire

- [ ] **Photos galerie** : remplacer les URLs Picsum dans `templates/index.html` (section galerie)
- [ ] **Photo hero** : remplacer le dégradé CSS par une vraie photo dans `static/css/style.css` (classe `.hero`)
- [ ] **Menus** : compléter les `<option>` dans les `<select>` de menus dans `templates/index.html`
- [ ] **Cagnotte** : remplacer `href="#"` du bouton cagnotte par l'URL réelle
- [ ] **Hébergements** : compléter les cartes d'hébergement dans `templates/index.html`
- [ ] **Mots de passe** : définir `SITE_PASSWORD` et `ADMIN_PASSWORD` dans `.env` (prod)
- [ ] **Favicon** : ajouter `static/favicon.ico` et la balise dans `templates/base.html`

---

*Avec amour, Joyce & Franck 💛 — 19 · 09 · 2026*
