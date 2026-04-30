# Document de cadrage - Plateforme Cloud d’Analyse Temps Réel des Marchés Financiers

## 1. Contexte et motivation

L’évolution rapide des marchés financiers et la volatilité croissante rendent indispensable l’accès à des outils d’analyse temps réel pour les investisseurs et analystes. Les solutions traditionnelles sont souvent coûteuses, peu flexibles ou réservées à des acteurs majeurs. L’objectif de ce projet est de concevoir une plateforme cloud moderne, ouverte et évolutive, permettant de collecter, traiter, analyser et visualiser en temps réel des données boursières, tout en intégrant des capacités de Machine Learning pour la prédiction de tendances.

## 2. Problématique

Comment fournir, via une architecture cloud scalable, une solution temps réel d’analyse et de prédiction sur des flux boursiers, accessible à tous, fiable et facilement déployable ?

## 3. Analyse du contexte
- Besoin d’accès temps réel à des données financières (API Finnhub)
- Nécessité de traiter de gros volumes de données (scalabilité)
- Importance de la visualisation et de l’interactivité (dashboard)
- Valeur ajoutée du Machine Learning pour la prédiction
- Contraintes de sécurité, coût, et simplicité de déploiement

## 4. Architecture détaillée

### Schéma global

```
[API Finnhub] → [Producer Kafka] → [Kafka (AWS MSK)] → [Consumer] → [Stockage S3/DB] → [Dashboard Streamlit/ML]
```

### Description des composants
- **Producer** : Récupère les données Finnhub et les publie sur Kafka (AWS MSK).
- **Kafka (MSK)** : Assure la transmission temps réel et la résilience du flux de données.
- **Consumer** : Consomme les messages Kafka, traite/filtre les données, les stocke (S3 ou base de données).
- **Stockage** : S3 (données brutes et traitées), éventuellement base SQL/NoSQL pour l’historique.
- **Dashboard Streamlit** : Visualisation temps réel, filtres, graphiques, indicateurs clés.
- **ML (SageMaker ou EC2)** : Prédiction de tendance, affichage des résultats sur le dashboard.
- **Sécurité** : IAM, VPC, gestion des secrets (AWS Secrets Manager).
- **Monitoring** : CloudWatch, logs, alertes.

### Schéma d’architecture (exemple)

![Schéma d’architecture](https://i.imgur.com/8Qw1QwF.png)

## 5. Justification de l’approche
- **Scalabilité** : Kafka (MSK) et S3 permettent de gérer de gros volumes et des pics de charge.
- **Flexibilité** : Architecture modulaire, chaque composant peut évoluer indépendamment.
- **Coût** : Utilisation de services managés (MSK, S3, SageMaker) pour optimiser le coût et la maintenance.
- **Sécurité** : IAM, VPC, gestion des accès et des secrets.
- **Évolutivité** : Possibilité d’ajouter d’autres sources de données, d’autres modèles ML, etc.

## 6. Pertinence et perspectives
Cette approche permet de répondre efficacement à la problématique : accès temps réel, analyse avancée, déploiement cloud, sécurité. Elle est adaptée à d’autres domaines (IoT, logistique, santé…). Perspectives : ajout d’alertes automatiques, d’API REST, d’authentification, de reporting avancé, etc.

---

*Document rédigé par le groupe – 2026*