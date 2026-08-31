# Cahier des charges — Hosfiital

## 1. Présentation du projet

### 1.1 Nom du projet

**Hosfiital**

> Nom volontairement orthographié ainsi.

### 1.2 Intitulé

**Hosfiital — Système BI d’aide à la décision pour le pilotage hospitalier**

### 1.3 Contexte

Les établissements hospitaliers produisent quotidiennement un volume important de données liées à leur activité : admissions, sorties, occupation des services, ressources humaines, dépenses, consommation énergétique, activité des différents services, etc.

Ces données sont généralement dispersées dans plusieurs systèmes ou sources et sont principalement utilisées pour les besoins opérationnels. L’objectif de Hosfiital est de les intégrer dans un système décisionnel permettant à la direction de disposer d’une vision consolidée de l’activité hospitalière.

Le projet s’inscrit dans le domaine de la **Business Intelligence (BI)** et de l’**intégration de données**, sans viser une architecture Big Data.

### 1.4 Problématique

**Comment intégrer les données provenant des différentes activités d’un hôpital afin de fournir, à un instant donné, une analyse consolidée de la situation et des recommandations utiles à la prise de décision de la direction ?**

---

# 2. Objectifs

## 2.1 Objectif général

Développer une plateforme BI permettant à la direction d’un hôpital de consulter les indicateurs clés de performance et de lancer, à la demande, une analyse de la situation afin d’obtenir des recommandations décisionnelles.

## 2.2 Objectifs spécifiques

Le système devra permettre de :

- collecter des données provenant de différentes sources hospitalières ;
- intégrer et centraliser ces données ;
- nettoyer et contrôler leur qualité ;
- stocker les données dans une base relationnelle ;
- produire des indicateurs décisionnels ;
- analyser l’évolution de l’activité hospitalière ;
- détecter certaines situations anormales ou préoccupantes ;
- générer des recommandations à partir de règles métier et/ou de modèles analytiques ;
- présenter les résultats sous forme de tableaux de bord BI ;
- permettre à la direction de lancer manuellement une analyse à un instant T ;
- conserver l’historique des analyses et recommandations générées.

---

# 3. Périmètre du projet

## 3.1 Fonctionnalités incluses

Le projet couvre principalement les domaines suivants :

### Activité hospitalière

- admissions ;
- sorties ;
- évolution du nombre de patients ;
- activité par service ;
- taux d’occupation ;
- évolution de la demande.

### Ressources

- capacité des services ;
- nombre de lits ;
- effectifs par service ;
- disponibilité globale des ressources ;
- évolution de la charge des services.

### Finances

- budget prévisionnel ;
- dépenses ;
- comparaison budget/réalisé ;
- évolution des coûts ;
- détection de dépassements budgétaires prévisionnels.

### Consommation et infrastructure

- consommation énergétique ;
- évolution de la consommation ;
- comparaison entre consommation et activité ;
- détection d'anomalies de consommation.

### Analyse décisionnelle

Le système pourra produire des recommandations concernant notamment :

- l’évolution de la capacité hospitalière ;
- les besoins en ressources humaines ;
- les investissements ;
- les risques de saturation ;
- les dépassements budgétaires ;
- les anomalies de consommation ;
- l’évolution prévisionnelle de l’activité.

---

# 4. Hors périmètre

Pour conserver un périmètre cohérent avec un projet BI et d’intégration de données, les éléments suivants ne font pas partie de la première version.

## 4.1 Décisions médicales

Le système ne devra pas :

- diagnostiquer des patients ;
- proposer des traitements ;
- prendre des décisions médicales ;
- remplacer le personnel médical.

## 4.2 Décisions opérationnelles individuelles

Le système ne devra pas décider directement :

- quel patient doit être traité ;
- quel infirmier doit s'occuper d'un patient ;
- quel lit doit être attribué à un patient ;
- quelle salle doit être attribuée à un patient ;
- quel médecin doit prendre en charge un patient.

Les données opérationnelles peuvent être utilisées comme **sources d'information**, mais les recommandations produites sont destinées à la direction.

## 4.3 Décisions automatiques

La première version ne prendra pas automatiquement de décision et ne déclenchera pas automatiquement d'action.

Le système produit une **recommandation** et laisse la décision finale à un responsable humain.

## 4.4 Analyse automatique continue

La première version ne réalisera pas d'analyse périodique ou automatique.

L'analyse sera effectuée **à la demande de l'utilisateur**, lorsqu'il clique sur une action du type :

> **Analyser maintenant**

L'analyse automatique en continu pourra faire partie d'une version ultérieure.

---

# 5. Utilisateurs concernés

## 5.1 Utilisateur principal

### Direction de l’hôpital

La direction constitue la cible principale du système.

Elle doit pouvoir :

- consulter les KPI ;
- consulter les tableaux de bord ;
- consulter l'état global de l'hôpital ;
- lancer une analyse ;
- consulter les recommandations ;
- consulter l'historique des analyses.

## 5.2 Sources opérationnelles

Les services opérationnels ne constituent pas la cible décisionnelle principale.

Leurs données servent de sources au système :

```text
Services hospitaliers
        ↓
     Données
        ↓
      Hosfiital
        ↓
Analyse décisionnelle
        ↓
     Direction
```

---

# 6. Architecture fonctionnelle

L'architecture générale du système sera organisée comme suit :

```text
┌───────────────────────────────────────────┐
│          SOURCES DE DONNÉES               │
│                                           │
│ Admissions / Services / RH / Finances /  │
│ Consommation / Activité                   │
└────────────────────┬──────────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │  Ingestion   │
              │ des données  │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │ ETL / ELT    │
              │ Nettoyage    │
              │ Validation   │
              │ Transformation│
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │ PostgreSQL   │
              │ Base centrale│
              └──────┬───────┘
                     │
          ┌──────────┴───────────┐
          │                      │
          ▼                      ▼
   ┌──────────────┐      ┌────────────────┐
   │   Metabase   │      │ Moteur         │
   │     BI       │      │ d'analyse      │
   └──────┬───────┘      └────────┬───────┘
          │                        │
          ▼                        ▼
   Dashboards KPI          Recommandations
          │                        │
          └───────────┬────────────┘
                      ▼
                 DIRECTION
```

---

# 7. Technologies prévues

## 7.1 Base de données

**PostgreSQL**

Rôle :

- stockage central des données ;
- stockage des données intégrées ;
- stockage des résultats d'analyse ;
- stockage de l'historique des recommandations.

La base PostgreSQL sera exécutée dans Docker.

## 7.2 BI

**Metabase**

Rôle :

- tableaux de bord ;
- KPI ;
- graphiques ;
- filtres ;
- exploration des données ;
- visualisation de l'évolution des indicateurs.

## 7.3 Backend / API

**Python + FastAPI**

Rôle :

- réception des données ;
- exposition des API ;
- déclenchement des traitements ;
- communication entre les différentes parties du système.

## 7.4 ETL

**Python**

Les traitements ETL permettront :

1. d'extraire les données ;
2. de les contrôler ;
3. de les nettoyer ;
4. de les transformer ;
5. de les charger dans PostgreSQL.

Des bibliothèques telles que Pandas pourront être utilisées.

## 7.5 Moteur décisionnel

**Python**

Le moteur analysera les indicateurs et appliquera des règles métier afin de générer des recommandations.

Exemple :

```text
SI
    taux_occupation > seuil
ET
    tendance_activité > seuil
ALORS
    niveau_risque = élevé
    recommandation = "Étudier une augmentation de capacité"
```

## 7.6 Conteneurisation

**Docker + Docker Compose**

Les principaux services seront isolés dans des conteneurs.

---

# 8. Gestion des données

## 8.1 Sources de données

Pour la première version, les données pourront être :

- simulées ;
- importées depuis des fichiers CSV ;
- reçues via API ;
- générées par un système de simulation.

L'utilisation de données hospitalières réelles n'est pas nécessaire.

## 8.2 Données simulées

Un générateur de données pourra produire des événements et des données hospitalières réalistes.

Exemples :

```text
Admission
Sortie
Occupation
Activité d'un service
Dépense
Consommation énergétique
Effectif
Budget
```

## 8.3 Qualité des données

Le pipeline devra effectuer plusieurs contrôles :

- valeurs manquantes ;
- valeurs incohérentes ;
- doublons ;
- types incorrects ;
- valeurs hors limites ;
- dates invalides.

---

# 9. Modèle décisionnel

Le système ne doit pas seulement afficher des données.

Il doit transformer :

```text
Données
   ↓
Informations
   ↓
Indicateurs
   ↓
Analyse
   ↓
Interprétation
   ↓
Recommandation
```

## 9.1 Exemple

Données :

```text
Occupation moyenne : 91 %
Croissance activité : +14 %
Capacité disponible : faible
```

Analyse :

```text
La capacité actuelle risque de devenir
insuffisante compte tenu de la tendance
d'activité.
```

Recommandation :

```text
Étudier une augmentation de la capacité
du service concerné.
```

La recommandation est présentée à la direction.

La décision finale reste humaine.

---

# 10. Analyse à la demande

La première version du système reposera sur une analyse déclenchée manuellement.

## 10.1 Fonctionnement

```text
Direction
    ↓
"Clique sur Analyser maintenant"
    ↓
Récupération des données actuelles
    ↓
Calcul des KPI
    ↓
Analyse
    ↓
Application des règles décisionnelles
    ↓
Génération des recommandations
    ↓
Affichage des résultats
```

## 10.2 Instant T

Chaque analyse devra être associée à :

- une date ;
- une heure ;
- les indicateurs calculés ;
- les anomalies détectées ;
- les recommandations générées.

Cela permettra de conserver une photographie décisionnelle de la situation à un instant donné.

---

# 11. Exemples de recommandations

### Capacité

```text
Occupation moyenne : 92 %
Tendance : +8 %

Recommandation :
Étudier une augmentation de la capacité
du service concerné.
```

### Ressources humaines

```text
Activité du service : +21 %
Charge moyenne : élevée
Effectifs : constants

Recommandation :
Évaluer le besoin de renforcer les effectifs
du service.
```

### Budget

```text
Budget annuel prévu : 500 M Ar
Projection actuelle : 620 M Ar

Dépassement prévisionnel : +24 %

Recommandation :
Réévaluer les dépenses et le budget
prévisionnel du service.
```

### Investissement

```text
Utilisation d'un équipement : 93 %
Demande : +28 %
Tendance : croissante

Recommandation :
Étudier l'opportunité d'un investissement
dans une capacité supplémentaire.
```

---

# 12. Tableau de bord BI

Le dashboard principal sera destiné à la direction.

Il pourra présenter :

## KPI généraux

- nombre de patients ;
- nombre d'admissions ;
- nombre de sorties ;
- taux global d'occupation ;
- activité des services ;
- dépenses ;
- budget ;
- consommation énergétique.

## Visualisations

- évolution de l'activité ;
- occupation par service ;
- évolution des dépenses ;
- comparaison budget/réalisé ;
- consommation énergétique ;
- tendances ;
- indicateurs de risque.

## Zone décisionnelle

Une zone spécifique pourra présenter :

```text
⚠️ ALERTES

Risque de saturation
Dépassement budgétaire prévisionnel
Anomalie de consommation
Capacité potentiellement insuffisante
```

et :

```text
RECOMMANDATIONS

→ Étudier une augmentation de capacité
→ Réévaluer le budget
→ Étudier un investissement
```

---

# 13. Historique des analyses

Chaque analyse réalisée devra être conservée.

Exemple :

```text
Analyse #001
Date : 31/08/2026
Heure : 14:00

Risque : Moyen
Occupation : 84 %

Recommandation :
Surveiller l'évolution de la capacité.
```

Puis :

```text
Analyse #002
Date : 31/08/2026
Heure : 16:00

Risque : Élevé
Occupation : 91 %

Recommandation :
Étudier une augmentation de capacité.
```

Cette fonctionnalité permettra à la direction de comparer l'évolution de la situation.

---

# 14. Sécurité et confidentialité

Même si les données utilisées pour le projet seront principalement simulées, l'application devra respecter une architecture compatible avec des données sensibles.

Principes :

- authentification ;
- autorisation par rôle ;
- accès limité aux données ;
- séparation des responsabilités ;
- absence de données médicales sensibles dans les démonstrations ;
- journalisation des analyses importantes.

Le rôle principal de la première version sera :

```text
ROLE_DIRECTION
```

---

# 15. Version 1 du projet

La première version devra obligatoirement fournir :

- [ ] PostgreSQL fonctionnel ;
- [ ] Metabase fonctionnel ;
- [ ] modèle de données hospitalier ;
- [ ] données simulées ;
- [ ] pipeline ETL ;
- [ ] API FastAPI ;
- [ ] calcul des KPI ;
- [ ] moteur de règles décisionnelles ;
- [ ] bouton « Analyser maintenant » ;
- [ ] génération de recommandations ;
- [ ] dashboard direction ;
- [ ] historique des analyses.

---

# 16. Évolution prévue — Version 2

L'analyse automatique ne fait **pas partie de la première version**.

Elle pourra être ajoutée ultérieurement.

### Version 2 : analyse automatique

```text
Données
   ↓
ETL
   ↓
PostgreSQL
   ↓
Analyse automatique périodique
   ↓
Détection d'une situation importante
   ↓
Recommandation
   ↓
Notification à la direction
```

Exemples :

- analyse toutes les heures ;
- détection automatique des anomalies ;
- alertes ;
- notifications ;
- prévisions ;
- modèles de Machine Learning.

Cette évolution sera développée séparément afin de ne pas complexifier inutilement la première version.

---

# 17. Contraintes techniques

- Le projet doit fonctionner sous Linux.
- Les services principaux doivent être conteneurisés avec Docker.
- La base de données principale doit être PostgreSQL.
- La solution BI doit être accessible via navigateur.
- Le système ne doit pas dépendre d'une infrastructure Big Data.
- Les données doivent pouvoir être simulées pour les démonstrations.
- Les composants doivent être suffisamment légers pour fonctionner sur une machine de développement standard.
- Les traitements doivent être reproductibles.

---

# 18. Critères de réussite

Le projet sera considéré comme fonctionnel lorsque le scénario suivant pourra être démontré :

```text
1. Des données hospitalières sont disponibles.
             ↓
2. Les données sont intégrées.
             ↓
3. Les données sont nettoyées et stockées.
             ↓
4. PostgreSQL contient les données.
             ↓
5. La direction consulte le dashboard BI.
             ↓
6. La direction clique sur "Analyser maintenant".
             ↓
7. Le système analyse la situation à l'instant T.
             ↓
8. Le moteur décisionnel identifie les problèmes.
             ↓
9. Des recommandations sont générées.
             ↓
10. Les résultats sont présentés à la direction.
             ↓
11. L'analyse est enregistrée dans l'historique.
```

---

# 19. Exemple de scénario de démonstration

Une simulation génère progressivement une augmentation de l'activité hospitalière.

Au départ :

```text
Occupation : 72 %
Activité : normale
Risque : faible
```

Plus tard :

```text
Occupation : 84 %
Activité : +10 %
Risque : moyen
```

Puis :

```text
Occupation : 92 %
Activité : +18 %
Risque : élevé
```

La direction clique sur :

> **Analyser maintenant**

Hosfiital produit :

```text
ANALYSE À 16:30

Situation :
Le taux d'occupation est élevé et la demande
présente une tendance à la hausse.

Risque :
Élevé

Recommandation :
Étudier une augmentation de la capacité
du service concerné.
```

La direction reste responsable de la décision finale.

---

# 20. Résultat attendu

Hosfiital doit fournir une chaîne complète :

```text
        DONNÉES HOSPITALIÈRES
                  ↓
             INTÉGRATION
                  ↓
                 ETL
                  ↓
             POSTGRESQL
                  ↓
            BUSINESS INTELLIGENCE
                  ↓
               ANALYSE
                  ↓
        MOTEUR DÉCISIONNEL
                  ↓
          RECOMMANDATIONS
                  ↓
              DIRECTION
                  ↓
         DÉCISION HUMAINE
```

Le projet constitue ainsi une solution de **Business Intelligence et d'intégration de données orientée aide à la décision**, avec une première version centrée sur l'**analyse à la demande**.

L'analyse automatique et les notifications automatiques sont volontairement réservées à une future version.
