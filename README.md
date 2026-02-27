# MailKern 🔍

MailKern est une plateforme open-source d'email intelligence. Elle permet de valider l'existence réelle d'adresses emails et de retrouver des contacts via des méthodes d'enrichissement (Pattern Matching & SMTP Ping) sans frais d'API.

## ✨ Fonctionnalités clés
- **Validation Syntaxique :** Vérification stricte du format (Regex).
- **Vérification DNS/MX :** Contrôle de la capacité du domaine à recevoir des mails.
- **SMTP Deep Check :** Interrogation directe des serveurs de mail (0€ coût).
- **Email Finder :** Générateur intelligent basé sur Nom/Prénom/Domaine.
- **Architecture Scalable :** Traitement asynchrone via Redis pour les listes massives.

## 🛠 Stack Technique
- **Frontend :** Next.js 16 (App Router), Tailwind CSS.
- **Backend :** Python 3.11, FastAPI.
- **Base de données :** PostgreSQL.
- **File d'attente :** Redis.
- **Infrastructure :** Docker & Docker Compose.

## ⚖️ Licence
Distribué sous licence MIT. Voir `LICENSE` pour plus d'informations.