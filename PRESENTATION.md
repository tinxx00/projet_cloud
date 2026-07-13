# 🎤 Script de soutenance — MarketPilot

Guide de présentation : accroche commerciale → démonstration → technique → Q&R.
Durée cible : ~12-15 min de présentation + démo, puis questions.

---

## Plan de la présentation

| Partie | Durée | Objectif |
|---|---|---|
| 1. Accroche commerciale | 2 min | Capter l'attention, poser le problème & la solution |
| 2. Démonstration produit | 3-4 min | Montrer que ça marche, côté utilisateur |
| 3. Architecture technique | 5-6 min | Expliquer comment c'est construit |
| 4. Choix & justifications | 2 min | Montrer que les décisions sont réfléchies |
| 5. Limites & perspectives | 1 min | Honnêteté = crédibilité |
| 6. Questions | — | Voir Q&R anticipées en annexe |

---

## Partie 1 — Accroche commerciale (le POURQUOI)

> **À dire (accroche) :**
> « Imaginez : vous êtes trader, ou simplement passionné de bourse. Chaque jour,
> des milliers de mouvements de marché se produisent. Les repérer au bon moment,
> c'est la différence entre saisir une opportunité… et la rater.
>
> Aujourd'hui, les outils qui font ça sont soit **très chers**, soit **complexes**,
> soit réservés aux grandes institutions. »

> **Le problème (à énoncer clairement) :**
> - Volatilité croissante des marchés.
> - Outils d'analyse coûteux, peu flexibles, réservés aux pros.
> - Difficulté à réagir **en temps réel** et à **ne rien rater**.

> **La solution :**
> « Nous avons créé **MarketPilot** : une plateforme cloud qui capte les marchés
> en temps réel, laisse l'**intelligence artificielle** repérer les tendances, et
> vous **alerte automatiquement** au bon moment — le tout dans une interface simple. »

> **Proposition de valeur (3 promesses) :**
> 1. ⏱️ **Gagner du temps** — l'IA surveille pour vous, 24/7.
> 2. 🎯 **Décider plus vite** — des signaux clairs, sans jargon.
> 3. 🔔 **Ne rien rater** — des alertes email dès qu'une opportunité apparaît.

---

## Partie 2 — Démonstration produit (le QUOI / comment ça marche pour l'utilisateur)

> **Fil conducteur : « suivons le parcours d'un utilisateur. »**

**Étapes de la démo (click path) :**

1. **Page d'accueil / landing** → « Voici la vitrine : temps réel, signaux IA, alertes.
   Je crée un compte en un clic. »
2. **Tableau de bord (Accueil)** → « Vue d'ensemble : cours en direct, indicateurs clés,
   accès à tous les modules. »
3. **Tendances** → « Les mouvements du marché, graphiques et chandeliers. »
4. **Signal IA** → « Le cœur du produit : pour chaque action, l'IA donne une tendance
   — Haussier / Neutre / Baissier — et un niveau de confiance. Simple et actionnable. »
5. **Recommandations** → « Selon mon profil de risque, la plateforme me suggère des
   actifs. Et le profil s'**adapte** à mes retours. »
6. **Alertes** → « J'active les alertes email : je serai prévenu automatiquement,
   même sans ouvrir l'application. » *(montrer l'email de confirmation reçu)*
7. **Coach IA** → « Un assistant conversationnel pour interpréter les signaux. »

> **Le moment "waouh" :** montrer un **email d'alerte réellement reçu**.
> « Ça, c'est envoyé automatiquement par un service qui tourne en arrière-plan. »

---

## Partie 3 — Architecture technique (le COMMENT on l'a fait)

> **À dire (transition) :**
> « Maintenant, ouvrons le capot. Comment une cotation de marché devient une alerte
> dans votre boîte mail ? »

**Schéma à montrer :**
```
[API Finnhub] → [Producer] → [Kafka] → [Consumer] → [S3 / CSV] → [Dashboard + ML] → [Alertes]
```

### 3.1 Ingestion temps réel
- **Producer** : un programme Python interroge l'API **Finnhub** (cotations), et publie
  chaque message dans **Kafka**.
- **Kafka** : un système de **file de messages** distribué. Analogie : « un tapis roulant
  qui transporte les données de façon fiable, même en cas de pic de charge. »
- Pourquoi Kafka ? **scalabilité** et **résilience** : si un composant tombe, rien n'est perdu.

### 3.2 Traitement
- **Consumer** : lit le flux Kafka, **nettoie et enrichit** chaque tick (variation absolue,
  variation en %, direction hausse/baisse), puis écrit dans un CSV / **S3**.
- **Fallback** : si Kafka est silencieux, le consumer bascule sur le CSV de backup → robustesse.

### 3.3 Machine Learning
- **Features** : à partir de l'historique (yfinance), on calcule ~20 indicateurs techniques
  (RSI, MACD, EMA, Bollinger, ATR, momentum…).
- **Entraînement sur AWS SageMaker** : un **Training Job** entraîne le modèle (container
  scikit-learn, instance `ml.m5.large`), avec **validation croisée temporelle** (walk-forward)
  et comparaison de plusieurs modèles → sélection du meilleur.
- **Stockage** : le modèle entraîné est sauvegardé sur **S3**.
- **Inférence locale** : le dashboard télécharge le modèle et calcule les prédictions en local.
  → **Pas d'endpoint SageMaker** = **pas de coût de serving continu**. Choix économique assumé.

### 3.4 Dashboard & alertes
- **Dashboard** : application **Streamlit** multi-pages (Python), graphiques **Plotly**.
- **Worker d'alertes** : un **service autonome** qui vérifie régulièrement les signaux pour
  tous les comptes abonnés et envoie les emails via **SMTP** — indépendamment du dashboard.

### 3.5 Cloud AWS
- **EC2** : les serveurs (Kafka, producer/consumer, dashboard).
- **S3** : stockage des données et des modèles.
- **SageMaker** : entraînement ML à la demande.
- **Athena** : requêtes SQL directement sur les données S3.
- **CloudWatch** : logs et supervision.

---

## Partie 4 — Choix techniques & justifications (pour convaincre le jury)

| Décision | Justification |
|---|---|
| **Kafka** | Scalabilité + résilience du flux temps réel (vs. simple appel direct) |
| **Fallback CSV** | Robustesse : le système continue même si Kafka s'arrête |
| **SageMaker à la demande** | Entraînement cloud puissant, sans coût quand inutilisé |
| **Inférence locale (pas d'endpoint)** | Économie : pas de facturation de serving 24/7 |
| **Architecture modulaire** | Chaque composant évolue indépendamment |
| **Services managés (S3, SageMaker)** | Moins de maintenance, meilleure fiabilité |

---

## Partie 5 — Limites & perspectives (honnêteté = crédibilité)

> **À assumer (ça inspire confiance) :**
> - « La prédiction de direction quotidienne reste difficile : notre AUC est proche de 0.52,
>   c'est-à-dire un peu mieux que le hasard. C'est **attendu** sur ce type de cible — même
>   les acteurs institutionnels peinent. Le vrai levier serait de revoir le **cadrage** du
>   signal (horizon, features, cible). »
>
> **Perspectives :**
> - Ré-entraînement automatique planifié.
> - API REST publique.
> - Sources de données additionnelles (news, sentiment).
> - Kafka managé (MSK) et base de données pour l'historique.

---

## Annexe — Questions probables du jury & réponses

**Q : Pourquoi Kafka et pas un simple appel API direct ?**
> Pour la scalabilité et la résilience : Kafka découple ingestion et traitement, encaisse les
> pics, et ne perd pas de messages. On peut ajouter des consumers sans toucher au producer.

**Q : Le modèle est-il vraiment utile si l'AUC est ~0.52 ?**
> Honnêtement, la prédiction de direction pure est très bruitée — c'est un résultat réaliste.
> La valeur du projet est surtout dans l'**architecture temps réel complète** et la chaîne
> bout-en-bout ; le modèle est un composant améliorable via un meilleur cadrage.

**Q : Pourquoi ne pas déployer le modèle sur un endpoint SageMaker ?**
> Un endpoint est facturé en continu (à l'heure). Pour notre besoin, l'inférence locale sur
> l'EC2 suffit et coûte zéro en serving. On entraîne sur SageMaker, on infère en local.

**Q : Comment gérez-vous la sécurité ?**
> Mots de passe hachés en PBKDF2 salé, secrets hors du dépôt (`.gitignore`), accès AWS via IAM
> (rôle SageMaker dédié, security groups EC2 avec ports restreints).

**Q : Comment le système passe-t-il à l'échelle ?**
> Kafka et S3 gèrent de gros volumes ; on peut multiplier les consumers, et passer à MSK
> (Kafka managé) pour la production.

**Q : Que se passe-t-il si l'API Finnhub tombe ?**
> Le consumer bascule sur le CSV de backup ; le dashboard continue de fonctionner sur les
> dernières données disponibles.

**Q : Les alertes fonctionnent-elles vraiment ?**
> Oui — un worker autonome tourne en arrière-plan, vérifie les seuils avec un anti-spam, et
> envoie les emails via SMTP. *(montrer un email réel reçu)*

---

## Checklist avant la démo

- [ ] Dashboard lancé et accessible.
- [ ] Données de démo générées (`scripts/seed_demo_data.py`).
- [ ] Un email d'alerte / de confirmation reçu à montrer.
- [ ] Console AWS ouverte : EC2, S3, SageMaker (Training Jobs `Completed`).
- [ ] Schéma d'architecture affiché.
- [ ] Répétée à voix haute au moins une fois (timing).

---

*Conseil : commence fort (l'accroche), montre vite quelque chose qui marche (la démo),
puis explique la technique. On retient ce qu'on voit fonctionner.*
