#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Système d'envoi d'emails automatisé avec recherche Google et LLM
Auteur: MiniMax Agent
Date: 2025-10-04
"""

import json
import csv
import smtplib
import http.client
import logging
import schedule
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List, Optional
import requests
from concurrent.futures import ThreadPoolExecutor
import threading

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailAutomationSystem:
    def __init__(self, config_path: str = "config.json"):
        """Initialise le système d'automation d'emails"""
        self.config = self.load_config(config_path)
        self.sent_emails = []
        self.failed_emails = []
        
    def load_config(self, config_path: str) -> Dict:
        """Charge la configuration depuis le fichier JSON"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            raise

    def search_company_info(self, company_name: str) -> Dict:
        """Recherche des informations sur l'entreprise via Serper API"""
        try:
            conn = http.client.HTTPSConnection("google.serper.dev")
            payload = json.dumps({
                "q": f"{company_name} Maroc entreprise société",
                "location": self.config["serper"]["location"],
                "gl": self.config["serper"]["gl"]
            })
            headers = {
                'X-API-KEY': self.config["serper"]["api_key"],
                'Content-Type': 'application/json'
            }
            
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            search_results = json.loads(data.decode("utf-8"))
            logger.info(f"Recherche effectuée pour {company_name}")
            return search_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche pour {company_name}: {e}")
            return {"organic": []}

    

    def generate_personalized_email(self, company_name: str, Nom_ceo: str,Titre: str,
                               search_results: Dict) -> str:
        """Génère un email personnalisé avec OpenRouter LLM"""
        try:
            search_context = ""
            if "organic" in search_results and search_results["organic"]:
                for idx, result in enumerate(search_results["organic"][:3], 1):
                    search_context += f"{idx}. {result.get('title', '')}: {result.get('snippet', '')}\n"

            prompt = f"""Tu es un expert en rédaction d'emails professionnels en français.

Écris un email de candidature adressé à une personne précise:
- Entreprise: {company_name}
- Nom du Destinataire: {Nom_ceo} (si disponible, sinon ne pas mentionner)
- Candidat: Achraf Bouyalloul, jeune diplômé en Intelligence Artificielle / informatique
- Titre du Destinataire: {Titre} (si disponible, sinon ne pas mentionner)

Informations sur l'entreprise :
{search_context}

Exigences:
- Objet clair (pas "spontanée", mais "Candidature - Ingénieur IA/tech")
- Introduction: saluer, montrer que je me suis intéressé à {company_name}
- Lien avec l'entreprise: mettre en avant mon profil IA/ML adapté au domaine
- Demande: opportunité/offre pour jeunes diplômés motivés
- Motivation: expliquer que tu es motivé pour n'importe quelle opportunité dans le domaine informatique/IA, que tu souhaites apprendre et contribuer
- Compétences: IA, ML, Python, développement d'applications IA, MLOps
- Conclusion: polie et positive, demande un rendez-vous ou échange
- Pièces jointes: CV (eviter de dire "[pièce jointe: CV ]")
- Longueur: max 300 mots
- Style: naturel, humain, PAS robotique

IMPORTANT: Réponds EXACTEMENT dans ce format:
OBJET: [objet ici]
CORPS:
[corps du mail ici]"""

            # Appel à OpenRouter API
            headers = {
                "Authorization": f"Bearer {self.config['openrouter']['api_key']}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.config['openrouter']['model'],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.4
            }
            
            response = requests.post(
                self.config['openrouter']['base_url'] + "/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                email_content = result['choices'][0]['message']['content']
                logger.info(f"Email généré pour {company_name}")
                return email_content
            else:
                logger.error(f"Erreur API OpenRouter: {response.status_code}")
                return "Erreur génération email"
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération d'email pour {company_name}: {e}")
            return 'Erreur génération email'

    def parse_email_content(self, email_content: str) -> tuple:
        """Parse le contenu email pour extraire objet et corps"""
        try:
            lines = email_content.strip().split('\n')
            subject = ""
            body_lines = []
            
            # Debug
            logger.info(f"Contenu à parser (premières lignes): {lines[:3]}")
            
            # Recherche de l'objet
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                if line_stripped.startswith("OBJET:"):
                    subject = line_stripped.replace("OBJET:", "").strip()
                    logger.info(f"Objet trouvé: {subject}")
                    
                    # Cherche "CORPS:" dans les lignes suivantes
                    corps_start_idx = i + 1
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith("CORPS:"):
                            corps_start_idx = j + 1
                            break
                    
                    # Récupère tout après "CORPS:"
                    body_lines = lines[corps_start_idx:]
                    break
            
            # Si pas d'objet trouvé avec la méthode stricte
            if not subject:
                logger.warning("Aucun objet trouvé avec format OBJET:, tentative de parsing alternatif")
                
                # Prend la première ligne comme objet potentiel
                if lines:
                    first_line = lines[0].strip()
                    if len(first_line) < 100 and not first_line.startswith("Madame") and not first_line.startswith("Monsieur"):
                        subject = first_line
                        body_lines = lines[1:]
                    else:
                        subject = f"Candidature - Ingénieur IA/ML"
                        body_lines = lines
                else:
                    subject = f"Candidature - Ingénieur IA/ML"
                    body_lines = []
            
            # Nettoie le corps
            body = "\n".join(body_lines).strip()
            
            # Enlève les lignes "CORPS:" qui pourraient rester
            body = body.replace("CORPS:", "").strip()
            
            # Si pas de corps, utilise le contenu original
            if not body:
                body = email_content.replace(f"OBJET: {subject}", "").replace("CORPS:", "").strip()
            
            # Validation finale
            if not subject:
                subject = "Candidature - Ingénieur IA/ML"
            
            if not body:
                body = email_content
            
            logger.info(f"✅ Parsing réussi - Objet: '{subject}' | Corps: {len(body)} caractères")
            return subject.strip(), body.strip()
            
        except Exception as e:
            logger.error(f"❌ Erreur parsing email: {e}")
            return "Candidature - Ingénieur IA/ML", email_content

    def send_email(self, to_email: str, company_name: str, subject: str, body: str, 
                   cv_path: Optional[str] = None, scheduled: bool = False) -> bool:
        """Envoie l'email avec pièce jointe et planification"""
        try:
            # Validation des paramètres
            if not subject or not subject.strip():
                subject = f"Candidature - Ingénieur IA/ML - {company_name}"
                logger.warning(f"Objet vide détecté, utilisation de: {subject}")
            
            # Configuration SMTP
            smtp_server = smtplib.SMTP(self.config['email']['smtp_server'], 
                                     self.config['email']['smtp_port'])
            smtp_server.starttls()
            smtp_server.login(self.config['email']['email'], 
                            self.config['email']['password'])

            # Création du message
            msg = MIMEMultipart()
            msg['From'] = f"{self.config['email']['from_name']} <{self.config['email']['email']}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            logger.info(f"📧 Préparation email - Objet: '{subject}' | Destinataire: {to_email}")
            
            # Headers pour la planification si demandée
            if scheduled:
                tomorrow_8am = datetime.now() + timedelta(days=1)
                tomorrow_8am = tomorrow_8am.replace(hour=8, minute=0, second=0, microsecond=0)
                
                msg['X-Delayed-Delivery-Time'] = tomorrow_8am.strftime('%Y-%m-%d %H:%M:%S')
                msg['X-Schedule-Send'] = tomorrow_8am.strftime('%Y-%m-%d %H:%M:%S')
                msg['Date'] = tomorrow_8am.strftime('%a, %d %b %Y %H:%M:%S %z')

            # Corps de l'email avec signatures
            email_body = f"""{body}

"""

            msg.attach(MIMEText(email_body, 'plain', 'utf-8'))

            # Pièce jointe CV - Recherche multiple
            cv_attached = False
            cv_possible_paths = [
                cv_path,
                "CV_ACHRAF_BOUYALLOUL_PFE.pdf",
                "CV_Achraf_Bouyalloul.pdf",
                "cv.pdf",
                "CV.pdf",
                "../CV_Achraf_Bouyalloul.pdf"
            ]
            
            for possible_path in cv_possible_paths:
                if possible_path and Path(possible_path).exists():
                    try:
                        with open(possible_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= CV_Achraf_Bouyalloul.pdf'
                            )
                            msg.attach(part)
                            cv_attached = True
                            logger.info(f"CV attaché depuis: {possible_path}")
                            break
                    except Exception as e:
                        logger.warning(f"Erreur pièce jointe {possible_path}: {e}")
                        continue
            
            if not cv_attached:
                logger.warning("⚠️ Aucun CV trouvé pour pièce jointe")

            # Envoi
            text = msg.as_string()
            smtp_server.sendmail(self.config['email']['email'], to_email, text)
            smtp_server.quit()
            
            status_msg = "avec CV" if cv_attached else "sans CV"
            scheduled_msg = " (PLANIFIÉ)" if scheduled else ""
            logger.info(f"✅ Email envoyé {status_msg} à {to_email} ({company_name}){scheduled_msg}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi à {to_email} ({company_name}): {e}")
            return False

    def process_person(self, person_data: Dict, cv_path: Optional[str] = None, scheduled: bool = False) -> Dict:
        """Traite une personne: recherche + génération + envoi"""
        company_name = person_data['company_name']
        Nom_ceo = person_data.get('Nom_ceo')
        Titre = person_data.get('Titre')
        email = person_data['email']
        
        logger.info(f"🏢 Traitement de {company_name} - <{email}>")
        
        try:
            # Recherche Google pour contextualiser l'entreprise
            search_results = self.search_company_info(company_name)
            
            # Génération email personnalisé
            email_content = self.generate_personalized_email(
                company_name, Nom_ceo ,Titre,search_results
            )
            
            # Parse email
            subject, body = self.parse_email_content(email_content)
            
            # Envoi
            success = self.send_email(email, company_name, subject, body, cv_path, scheduled)
            
            result = {
                'company': company_name,
                'email': email,
                'subject': subject,
                'body_length': len(body),
                'success': success,
                'scheduled': scheduled,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                self.sent_emails.append(result)
            else:
                self.failed_emails.append(result)
                
            return result
        
        except Exception as e:
            logger.error(f"💥 Erreur lors du traitement de ({company_name}): {e}")
            return {"success": False, "error": str(e)}

    def load_companies(self, csv_path: str) -> List[Dict]:
        """Charge la liste des personnes depuis CSV"""
        companies = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    companies.append({
                        'company_name': row['company_name'],
                        'email': row['email'],
                        'Nom_ceo': row['Nom_ceo'],
                        'Titre': row['Titre']
                    })
            logger.info(f"Chargé {len(companies)} contacts")
            return companies
        except Exception as e:
            logger.error(f"Erreur lors du chargement du CSV: {e}")
            return []

    def run_email_campaign(self, csv_path: str, cv_path: Optional[str] = None, 
                          max_workers: int = 3, delay_between_emails: int = 10,
                          scheduled: bool = False):
        """Lance la campagne d'emails"""
        schedule_msg = " PLANIFIÉE" if scheduled else ""
        logger.info(f"🚀 === DÉBUT CAMPAGNE EMAIL{schedule_msg} ===")
        
        companies = self.load_companies(csv_path)
        if not companies:
            logger.error("❌ Aucune entreprise chargée")
            return
        
        logger.info(f"📊 Traitement de {len(companies)} entreprises")
        
        # Vérification CV
        cv_status = "✅ AVEC CV" if cv_path and Path(cv_path).exists() else "⚠️ SANS CV"
        logger.info(f"📎 Statut CV: {cv_status}")
        
        # Traitement séquentiel avec délai pour éviter le spam
        for i, company in enumerate(companies, 1):
            logger.info(f"📧 [{i}/{len(companies)}] Traitement en cours...")
            
            result = self.process_person(company, cv_path, scheduled)
            
            # Délai entre emails sauf pour le dernier
            if i < len(companies):
                logger.info(f"⏱️ Attente {delay_between_emails}s avant le prochain email...")
                time.sleep(delay_between_emails)
        
        # Rapport final
        self.generate_report()
        
        logger.info(f"🏁 === FIN CAMPAGNE EMAIL{schedule_msg} ===")

    def schedule_campaign_immediate(self, csv_path: str, cv_path: Optional[str] = None):
        """Lance la campagne avec envoi planifié immédiat (headers de planification)"""
        logger.info("🕐 Lancement de la campagne avec PLANIFICATION FORCÉE dans les emails")
        logger.info("📅 Emails configurés pour être livrés demain matin à 8h00")
        
        # Lance la campagne avec le flag scheduled=True
        self.run_email_campaign(csv_path, cv_path, scheduled=True)

    def generate_report(self):
        """Génère un rapport de la campagne"""
        total = len(self.sent_emails) + len(self.failed_emails)
        success_rate = (len(self.sent_emails) / total * 100) if total > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_emails': total,
            'sent_successfully': len(self.sent_emails),
            'failed': len(self.failed_emails),
            'success_rate': f"{success_rate:.1f}%",
            'sent_emails': self.sent_emails,
            'failed_emails': self.failed_emails
        }
        
        # Sauvegarde du rapport
        with open(f'email_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 
                  'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"RAPPORT: {len(self.sent_emails)}/{total} emails envoyés avec succès ({success_rate:.1f}%)")
        
        if self.failed_emails:
            logger.warning(f"Échecs: {[e['company'] for e in self.failed_emails]}")

    def schedule_campaign(self, csv_path: str, cv_path: Optional[str] = None, 
                         schedule_time: str = "08:00"):
        """Planifie la campagne pour demain matin (méthode traditionnelle)"""
        logger.info(f"📅 Campagne planifiée pour demain à {schedule_time}")
        
        schedule.every().day.at(schedule_time).do(
            self.run_email_campaign, csv_path, cv_path, 30, False
        )
        
        logger.info("⏳ En attente de l'heure programmée...")
        logger.info("⚠️ Appuyez sur Ctrl+C pour arrêter")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Vérifie toutes les minutes
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt du planificateur")

def main():
    """Fonction principale"""
    print("🚀 === SYSTÈME D'AUTOMATION D'EMAILS ===\n")
    
    # Initialisation
    system = EmailAutomationSystem("config.json")
    
    # Chemins des fichiers
    csv_path = "filtered_achraf.csv" # Ajoutez votre fichier CSV
    cv_path = "CV_USER.pdf"  # Ajoutez votre CV
    
    # Menu amélioré
    print("📧 OPTIONS D'ENVOI:")
    print("1. 🚀 Lancer la campagne IMMÉDIATEMENT")
    print("2. ⏰ Planifier avec ATTENTE (script reste ouvert jusqu'à 8h00 demain)")
    print("3. 📅 PLANIFICATION FORCÉE (envoi immédiat avec headers de planification)")

    
    choice = input("\n🎯 Votre choix (1/2/3): ").strip()
    
    if choice == "1":
        print("🚀 Lancement immédiat de la campagne...")
        system.run_email_campaign(csv_path, cv_path)
    
    elif choice == "2":
        print("⏰ Planification traditionnelle - Le script va attendre...")
        system.schedule_campaign(csv_path, cv_path, "08:00")
    
    elif choice == "3":
        print("📅 PLANIFICATION FORCÉE - Envoi avec headers de livraison planifiée...")
        system.schedule_campaign_immediate(csv_path, cv_path)
    
    else:
        print("❌ Choix invalide")

if __name__ == "__main__":
    main()