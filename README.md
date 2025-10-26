# Système d'Automation d'Emails avec IA

## Description
Système automatisé d'envoi d'emails personnalisés aux entreprises marocaines avec :
- Recherche Google automatique via Serper API
- Génération d'emails personnalisés via LLM (OpenRouter)
- Envoi d'emails avec CV en pièce jointe
- Planification d'envoi
- Rapports détaillés

## Fonctionnalités
- ✅ Lecture CSV des entreprises
- ✅ Recherche automatique d'informations sur chaque entreprise
- ✅ Génération d'emails personnalisés avec IA
- ✅ Envoi SMTP avec pièces jointes
- ✅ Planification d'envoi (demain 8h00)
- ✅ Rapports et logs détaillés
- ✅ Gestion d'erreurs robuste

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
1. Modifiez `config.json` avec vos clés API
2. Ajoutez votre CV : `CV_Achraf_Bouyalloul.pdf`
3. Vérifiez la liste dans `companies.csv`

## Utilisation
```bash
python main.py
```

### Options disponibles :
1. **Lancement immédiat** : Envoie tous les emails maintenant
2. **Planification** : Planifie pour demain matin 8h00
3. **Test** : Test avec une seule entreprise


## Fonctionnement

1. **Recherche** : Pour chaque entreprise, recherche via Serper API
2. **Génération** : LLM génère un email personnalisé basé sur les résultats
3. **Envoi** : Email envoyé avec CV en pièce jointe
4. **Délai** : 30 secondes entre chaque email (anti-spam)
5. **Rapport** : Génère un rapport JSON avec statistiques

## Sécurité
- Délais anti-spam intégrés
- Gestion d'erreurs robuste
- Logs détaillés
- Configuration sécurisée

## Logs
Tous les événements sont loggés dans :
- `email_automation.log`
- Console en temps réel

## Rapports
Rapports JSON générés automatiquement :
- `email_report_YYYYMMDD_HHMMSS.json`

## Support
Auteur: Achraf BOUYALLOUL
Date: 2025-10-04