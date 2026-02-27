from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Domain(Base):
    """
    Modèle SQLAlchemy pour la table 'Domain'.
    Représente un domaine avec ses informations associées.
    """
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    domain_name = Column(String(255), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    detected_pattern = Column(String(255), nullable=True)

    # Relation avec les contacts
    contacts = relationship("Contact", back_populates="domain", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Domain(id={self.id}, domain_name={self.domain_name}, company_name={self.company_name})>"


class Contact(Base):
    """
    Modèle SQLAlchemy pour la table 'Contact'.
    Représente un contact associé à un domaine.
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=True, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relation avec le domaine
    domain = relationship("Domain", back_populates="contacts")

    def __repr__(self):
        return f"<Contact(id={self.id}, email={self.email}, domain_id={self.domain_id})>"
