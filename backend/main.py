from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import redis
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import init_db, SessionLocal, engine
from models import Domain, Contact  # noqa: F401 (pour que SQLAlchemy enregistre les modèles)
from email_service import EmailVerifier

# Configuration des connexions
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


def get_redis_connection():
    """Retourne une connexion Redis"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_db():
    """Dépendance pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Modèles Pydantic pour les requêtes/réponses
class EmailVerificationRequest(BaseModel):
    """Requête de vérification d'email"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    domain_id: Optional[int] = None


class EmailVerificationResponse(BaseModel):
    """Réponse de vérification d'email"""
    email: str
    status: str  # valid, invalid, unknown
    reason: str
    mx_record: Optional[str] = None
    smtp_server: Optional[str] = None
    contact_id: Optional[int] = None


class EmailFinderRequest(BaseModel):
    """Requête pour trouver un email"""
    first_name: str
    last_name: str
    domain: str


class EmailFinderResponse(BaseModel):
    """Réponse pour la recherche d'email"""
    email: str
    patterns_tested: int
    reason: str
    mx_record: Optional[str] = None
    smtp_server: Optional[str] = None
    contact_id: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère le cycle de vie de l'application FastAPI.
    - Au démarrage : initialise la base de données
    - À l'arrêt : nettoie les ressources
    """
    # Startup
    try:
        init_db()
        print("✅ Tables de base de données créées avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables : {str(e)}")
    
    yield
    
    # Shutdown
    engine.dispose()
    print("✅ Ressources libérées")


app = FastAPI(title="MailKern API", version="1.0.0", lifespan=lifespan)

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "Bienvenue sur MailKern API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Vérification de l'état des services (API, Redis, Base de données).
    Retourne le statut de chaque service.
    """
    status = {
        "api": "healthy",
        "redis": "unknown",
        "database": "unknown"
    }
    
    # Test Redis
    try:
        r = get_redis_connection()
        r.ping()
        status["redis"] = "healthy"
    except Exception as e:
        status["redis"] = f"unhealthy: {str(e)}"
    
    # Test PostgreSQL avec SQLAlchemy
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        status["database"] = "healthy"
    except Exception as e:
        status["database"] = f"unhealthy: {str(e)}"
    
    return status


@app.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    request: EmailVerificationRequest,
    db = Depends(get_db)
):
    """
    Endpoint pour vérifier une adresse email.
    
    Effectue une vérification complète :
    1. Validation syntaxique
    2. Vérification des enregistrements MX
    3. Vérification SMTP
    4. Sauvegarde/mise à jour en base de données
    
    Args:
        request: Objet contenant email, first_name, last_name, domain_id
        db: Session de base de données
        
    Returns:
        EmailVerificationResponse avec le statut de vérification
    """
    try:
        # Nettoyage de l'email
        email = request.email.strip().lower()
        
        # Initialise le vérificateur d'emails
        verifier = EmailVerifier(smtp_timeout=10)
        
        # Effectue la vérification complète
        verification_result = verifier.verify_email(email)
        
        # Détermine le statut final
        status = verification_result['status']  # 'valid', 'invalid', 'unknown'
        
        # Cherche ou crée un contact en base de données
        existing_contact = db.query(Contact).filter(Contact.email == email).first()
        
        if existing_contact:
            # Met à jour le contact existant
            existing_contact.status = status
            existing_contact.updated_at = datetime.utcnow()
            if request.first_name:
                existing_contact.first_name = request.first_name
            if request.last_name:
                existing_contact.last_name = request.last_name
            if request.domain_id:
                existing_contact.domain_id = request.domain_id
            contact = existing_contact
        else:
            # Crée un nouveau contact
            contact = Contact(
                email=email,
                first_name=request.first_name or "Unknown",
                last_name=request.last_name or "Unknown",
                status=status,
                domain_id=request.domain_id,
                updated_at=datetime.utcnow()
            )
        
        # Sauvegarde en base de données
        db.add(contact)
        db.commit()
        db.refresh(contact)
        
        # Retourne le résultat
        return EmailVerificationResponse(
            email=email,
            status=status,
            reason=verification_result['reason'],
            mx_record=verification_result['mx_record'],
            smtp_server=verification_result['smtp_server'],
            contact_id=contact.id
        )
        
    except Exception as e:
        db.rollback()
        print(f"Erreur lors de la vérification d'email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification: {str(e)}"
        )


@app.post("/find-email", response_model=EmailFinderResponse)
async def find_email(
    request: EmailFinderRequest,
    db = Depends(get_db)
):
    """
    Endpoint pour trouver l'adresse email d'une personne.
    
    Processus :
    1. Génère une liste de patterns d'emails possibles
    2. Teste chaque pattern via SMTP
    3. Dès qu'un email valide est trouvé, l'enregistre et l'arrête
    4. Retourne l'email trouvé ou une erreur 404 si aucun n'est valide
    
    Args:
        request: Objet contenant first_name, last_name, domain
        db: Session de base de données
        
    Returns:
        EmailFinderResponse avec l'email trouvé et les détails
        
    Raises:
        HTTPException 404: Si aucun email valide n'est trouvé
    """
    try:
        # Nettoyage des entrées
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        domain = request.domain.strip().lower()
        
        if not first_name or not last_name or not domain:
            raise HTTPException(
                status_code=400,
                detail="Les champs first_name, last_name et domain sont obligatoires"
            )
        
        # Initialise le vérificateur d'emails
        verifier = EmailVerifier(smtp_timeout=10)
        
        # Génère les patterns d'emails possibles
        patterns = verifier.generate_patterns(first_name, last_name, domain)
        
        if not patterns:
            raise HTTPException(
                status_code=400,
                detail="Impossible de générer des patterns d'emails"
            )
        
        # Teste chaque pattern
        found_email = None
        patterns_tested = 0
        verification_result = None
        
        for pattern in patterns:
            patterns_tested += 1
            print(f"[Email Finder] Testage du pattern: {pattern}")
            
            # Vérifie le pattern
            verification_result = verifier.verify_email(pattern)
            
            # Si l'email est valide, on l'enregistre et on arrête
            if verification_result['status'] == 'valid':
                found_email = pattern
                print(f"[Email Finder] ✅ Email trouvé: {found_email}")
                break
        
        # Si aucun email valide n'est trouvé
        if not found_email:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun email valide trouvé pour {first_name} {last_name} @ {domain} ({patterns_tested} patterns testés)"
            )
        
        # Enregistre l'email trouvé en base de données
        existing_contact = db.query(Contact).filter(Contact.email == found_email).first()
        
        if existing_contact:
            # Met à jour le contact existant
            existing_contact.status = 'valid'
            existing_contact.updated_at = datetime.utcnow()
            existing_contact.first_name = first_name
            existing_contact.last_name = last_name
            contact = existing_contact
        else:
            # Crée un nouveau contact
            contact = Contact(
                email=found_email,
                first_name=first_name,
                last_name=last_name,
                status='valid',
                domain_id=None,
                updated_at=datetime.utcnow()
            )
        
        # Sauvegarde en base de données
        db.add(contact)
        db.commit()
        db.refresh(contact)
        
        # Retourne le résultat
        return EmailFinderResponse(
            email=found_email,
            patterns_tested=patterns_tested,
            reason=verification_result['reason'],
            mx_record=verification_result['mx_record'],
            smtp_server=verification_result['smtp_server'],
            contact_id=contact.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erreur lors de la recherche d'email: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
