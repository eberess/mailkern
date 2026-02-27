"""
Service de vérification d'emails.
Valide la syntaxe, récupère les serveurs MX et vérifie l'existence via SMTP.
"""

import re
import socket
import smtplib
from typing import Optional, Dict
import dns.resolver
import dns.exception


class EmailVerifier:
    """
    Classe pour vérifier la validité des adresses email.
    Utilise la validation syntaxique, la vérification MX et la vérification SMTP.
    """

    # Regex pour la validation basique du format email
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )

    def __init__(self, smtp_timeout: int = 10):
        """
        Initialise le vérificateur d'emails.
        
        Args:
            smtp_timeout: Timeout en secondes pour les connexions SMTP
        """
        self.smtp_timeout = smtp_timeout

    def generate_patterns(self, first_name: str, last_name: str, domain: str) -> list:
        """
        Génère une liste de patterns d'emails possibles basés sur le prénom, nom et domaine.
        Les patterns sont générés dans un ordre de probabilité décroissante.
        
        Args:
            first_name: Prénom de la personne
            last_name: Nom de famille de la personne
            domain: Domaine de l'entreprise
            
        Returns:
            Liste de patterns d'emails à tester (ex: ['john.doe@domain.com', 'jdoe@domain.com', ...])
        """
        if not first_name or not last_name or not domain:
            return []
        
        # Nettoyage des entrées
        first = first_name.strip().lower()
        last = last_name.strip().lower()
        domain = domain.strip().lower()
        
        # Supprime les espaces et caractères spéciaux du domaine s'il n'en a pas
        if '@' not in domain:
            domain = domain
        else:
            # Si le domaine contient un @, on l'extrait
            domain = domain.split('@')[-1]
        
        patterns = []
        
        # Pattern 1: first.last@domain (très commun)
        patterns.append(f"{first}.{last}@{domain}")
        
        # Pattern 2: firstlast@domain
        patterns.append(f"{first}{last}@{domain}")
        
        # Pattern 3: first@domain (peut fonctionner pour certains)
        patterns.append(f"{first}@{domain}")
        
        # Pattern 4: last@domain
        patterns.append(f"{last}@{domain}")
        
        # Pattern 5: f.last@domain (initiale + nom)
        patterns.append(f"{first[0]}.{last}@{domain}")
        
        # Pattern 6: flast@domain (initiale + nom sans séparateur)
        patterns.append(f"{first[0]}{last}@{domain}")
        
        # Pattern 7: first_last@domain (underscores)
        patterns.append(f"{first}_{last}@{domain}")
        
        # Pattern 8: first-last@domain (tirets)
        patterns.append(f"{first}-{last}@{domain}")
        
        # Pattern 9: firstname.lastname@domain (pour les noms composés)
        patterns.append(f"first{first[1:]}.{last}@{domain}" if len(first) > 1 else f"{first}.{last}@{domain}")
        
        # Pattern 10: l.first@domain (nom + initiale du prénom)
        patterns.append(f"{last[0]}.{first}@{domain}")
        
        # Pattern 11: lfirst@domain
        patterns.append(f"{last[0]}{first}@{domain}")
        
        # Pattern 12: last.first@domain (ordre inverse)
        patterns.append(f"{last}.{first}@{domain}")
        
        # Supprime les doublons tout en conservant l'ordre
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                unique_patterns.append(pattern)
        
        return unique_patterns

    def check_syntax(self, email: str) -> bool:
        """
        Valide le format syntaxique d'une adresse email.
        
        Args:
            email: Adresse email à valider
            
        Returns:
            True si le format est valide, False sinon
        """
        if not email or not isinstance(email, str):
            return False
        
        # Nettoyage
        email = email.strip().lower()
        
        # Vérification avec regex
        if not self.EMAIL_REGEX.match(email):
            return False
        
        return True

    def get_mx_record(self, domain: str) -> Optional[str]:
        """
        Récupère le serveur de mail principal (MX record) d'un domaine.
        
        Args:
            domain: Domaine à vérifier
            
        Returns:
            Adresse du serveur MX ou None si non trouvé
        """
        try:
            # Interroge les enregistrements MX du domaine
            mx_records = dns.resolver.resolve(domain, 'MX')
            if mx_records:
                # Retourne le serveur MX avec la priorité la plus basse (la plus haute)
                return str(mx_records[0].exchange).rstrip('.')
            return None
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
            # Domaine non trouvé ou pas d'enregistrement MX
            return None
        except Exception as e:
            print(f"Erreur DNS pour {domain}: {str(e)}")
            return None

    def verify_smtp(self, email: str) -> Dict[str, any]:
        """
        Vérifie l'existence d'une adresse email via SMTP.
        Effectue un handshake SMTP complet :
        1. Connexion au serveur MX sur port 25
        2. Envoi de HELO/EHLO
        3. MAIL FROM avec une adresse bidon
        4. RCPT TO avec l'email cible
        5. Analyse des codes de réponse
        
        Args:
            email: Adresse email à vérifier
            
        Returns:
            Dict avec les résultats de vérification:
            {
                'status': 'valid' | 'invalid' | 'unknown',
                'message': str,
                'smtp_server': str ou None
            }
        """
        email = email.strip().lower()
        
        # Extraction du domaine
        if '@' not in email:
            return {
                'status': 'invalid',
                'message': 'Format email invalide',
                'smtp_server': None
            }
        
        domain = email.split('@')[1]
        
        # Récupère le serveur MX
        mx_server = self.get_mx_record(domain)
        if not mx_server:
            return {
                'status': 'unknown',
                'message': f'Aucun serveur MX trouvé pour {domain}',
                'smtp_server': None
            }
        
        # Tente de vérifier via SMTP
        try:
            # Connexion au serveur MX sur le port 25 avec timeout
            with smtplib.SMTP(mx_server, 25, timeout=self.smtp_timeout) as server:
                server.set_debuglevel(0)
                
                # Step 1: EHLO pour initier la connexion
                try:
                    server.ehlo()
                except smtplib.SMTPServerDisconnected:
                    # Fallback to HELO si EHLO échoue
                    server.helo()
                
                # Step 2: MAIL FROM avec une adresse bidon
                # Utilise une adresse générique pour ne pas révéler d'infos
                try:
                    server.mail('check@mailkern.com')
                except smtplib.SMTPNotSupportedError:
                    # Certains serveurs ne supportent pas MAIL FROM
                    pass
                except smtplib.SMTPServerDisconnected:
                    return {
                        'status': 'unknown',
                        'message': 'Serveur SMTP déconnecté après MAIL FROM',
                        'smtp_server': mx_server
                    }
                
                # Step 3: RCPT TO avec l'email cible
                # Code 250/251 = accepté, 550/551/552/553 = rejeté
                try:
                    code, response = server.rcpt(email)
                    response_msg = response.decode() if isinstance(response, bytes) else str(response)
                    
                    if code in [250, 251]:
                        # 250 = Requested mail action okay
                        # 251 = User not local; will forward
                        return {
                            'status': 'valid',
                            'message': f'Email valide (SMTP {code})',
                            'smtp_server': mx_server
                        }
                    elif code in [550, 551, 552, 553]:
                        # 550 = Mailbox unavailable
                        # 551 = User not local
                        # 552 = Exceeded storage allocation
                        # 553 = Mailbox name not allowed
                        return {
                            'status': 'invalid',
                            'message': f'Email invalide (SMTP {code}: {response_msg})',
                            'smtp_server': mx_server
                        }
                    else:
                        # Codes inconnus
                        return {
                            'status': 'unknown',
                            'message': f'Réponse SMTP inconnue: {code} {response_msg}',
                            'smtp_server': mx_server
                        }
                        
                except smtplib.SMTPServerDisconnected:
                    return {
                        'status': 'unknown',
                        'message': 'Serveur SMTP déconnecté après RCPT TO',
                        'smtp_server': mx_server
                    }
                except smtplib.SMTPRecipientsRefused:
                    # Récipients refusés
                    return {
                        'status': 'invalid',
                        'message': 'Adresse email refusée par le serveur SMTP',
                        'smtp_server': mx_server
                    }
                
        except socket.timeout:
            return {
                'status': 'unknown',
                'message': f'Timeout de connexion SMTP au serveur {mx_server} ({self.smtp_timeout}s)',
                'smtp_server': mx_server
            }
        except smtplib.SMTPConnectError as e:
            return {
                'status': 'unknown',
                'message': f'Erreur de connexion SMTP: {str(e)}',
                'smtp_server': mx_server
            }
        except smtplib.SMTPException as e:
            return {
                'status': 'unknown',
                'message': f'Erreur SMTP: {str(e)}',
                'smtp_server': mx_server
            }
        except Exception as e:
            return {
                'status': 'unknown',
                'message': f'Erreur inattendue: {str(e)}',
                'smtp_server': mx_server
            }

    def verify_email(self, email: str) -> Dict[str, any]:
        """
        Effectue une vérification complète d'une adresse email.
        
        Args:
            email: Adresse email à vérifier
            
        Returns:
            Dict avec les résultats complets de vérification
        """
        # Nettoyage
        email = email.strip().lower()
        
        # 1. Validation syntaxique
        if not self.check_syntax(email):
            return {
                'email': email,
                'status': 'invalid',
                'reason': 'Format email invalide',
                'smtp_server': None,
                'mx_record': None
            }
        
        # 2. Récupère le domaine et vérifie les MX records
        domain = email.split('@')[1]
        mx_record = self.get_mx_record(domain)
        
        if not mx_record:
            return {
                'email': email,
                'status': 'unknown',
                'reason': f'Domaine non trouvé ou pas d\'enregistrement MX',
                'smtp_server': None,
                'mx_record': None
            }
        
        # 3. Vérification SMTP
        smtp_result = self.verify_smtp(email)
        
        return {
            'email': email,
            'status': smtp_result['status'],
            'reason': smtp_result['message'],
            'smtp_server': smtp_result['smtp_server'],
            'mx_record': mx_record
        }
