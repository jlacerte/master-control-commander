# Master Control Commander

[English version](README.md)

**v0.1.0-alpha — Développement actif**

> Statut : Développement initial et consolidation. Architecture documentée à partir d'un système de production fonctionnel. Démo disponible pour test local.

Architecture à deux couches pour opérer des agents IA autonomes dans une entreprise réelle. Sépare l'orchestration d'infrastructure (**Commander**) de la logique des agents intelligents (**Control**).

Développé et testé sur 6+ mois dans une entreprise de services terrain — facturation, communications clients, intelligence de marché et maintenance système.

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │            MASTER CONTROL                    │
                    │         (Couche agents IA)                   │
                    │                                              │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
                    │  │Concierge │ │ Business │ │  Intel   │    │
                    │  │ Worker   │ │  Worker  │ │  Worker  │    │
                    │  │(Infra)   │ │(Revenus) │ │(Marché)  │    │
                    │  └────┬─────┘ └────┬─────┘ └────┬─────┘    │
                    │       └────────────┼────────────┘           │
                    │                    │                         │
                    │           Courtier de tâches                 │
                    │           (Supabase/SQLite)                  │
                    └────────────────────┬────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────────┐
                    │            MASTER COMMANDER                  │
                    │        (Couche infrastructure)               │
                    │                                              │
                    │  ┌─────────────────────────────────────┐    │
                    │  │       Flotte de serveurs MCP         │    │
                    │  │  ┌─────┐┌─────┐┌─────┐┌─────┐     │    │
                    │  │  │ ERP ││Email││ CRM ││Tél. │ ... │    │
                    │  │  └─────┘└─────┘└─────┘└─────┘     │    │
                    │  └─────────────────────────────────────┘    │
                    │                                              │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
                    │  │ Moniteur │ │   Auto-  │ │ Registre │    │
                    │  │  santé   │ │Stabilise │ │  ports   │    │
                    │  └──────────┘ └──────────┘ └──────────┘    │
                    │                                              │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
                    │  │ Mémoire  │ │Blueprint │ │Validation│    │
                    │  │   RAG    │ │  Refresh │ │Adversaire│    │
                    │  └──────────┘ └──────────┘ └──────────┘    │
                    └─────────────────────────────────────────────┘
```

### Commander (Infrastructure)

Maintient tout en opération sur un seul VPS avec systemd et cron :

| Composant | Rôle |
|-----------|------|
| Serveurs MCP (11+) | Abstraction d'API — ERP, Email, CRM, Téléphone, Calendrier |
| Workers (3) | Exécution autonome de tâches via Claude SDK |
| Jobs Cron (8+) | Vérifications de santé, sync de données, auto-stabilisation |
| Registre de ports | Prévention centralisée des conflits de ports |

### Control (Couche agents)

Chaque worker est une session Claude SDK avec :
- Autonomie basée sur le rôle (limites financières, portes d'approbation, actions interdites)
- Exécution pilotée par tâches (poll → exécute → rapporte)
- Expertise de domaine chargée via fichiers CLAUDE.md et RAG
- Disjoncteurs (max 3 échecs avant escalade)

---

## Patterns de conception

### 1. Boucle de worker universelle

```python
while True:
    health = check_health()          # Guardian : la santé conditionne l'exécution
    if health == "red":
        defer_all_tasks()
        continue

    task = broker.get_next(status="todo", assigned_to=ROLE)
    result = sdk_session.send(prompt=task, tools=ROLE_TOOLS)

    if result.success:
        broker.update(task.id, status="review")
    elif task.attempts >= MAX:
        broker.update(task.id, status="review")  # Disjoncteur
        escalate(task)
```

### 2. Pattern Guardian

Le statut de santé conditionne toutes les opérations. Aucun worker ne tente de tâches business quand l'infrastructure est dégradée.

```
GREEN  → Exécution normale
YELLOW → Capacités réduites
RED    → Tout différer, focus sur la récupération
```

### 3. Disjoncteur

Empêche les boucles de retry infinies — le mode de défaillance le plus courant des agents autonomes.

```
Tentative 1 échoue → retry
Tentative 2 échoue → retry
Tentative 3 échoue → arrêt, marquer "review", escalader
```

### 4. Abstraction MCP

Les agents voient des appels d'outils propres. Les serveurs MCP gèrent l'OAuth, le rate limiting, les retries et la normalisation des erreurs. L'agent ne touche jamais aux API brutes.

### 5. Matrice d'autonomie

Limites explicites par worker, définies dans CLAUDE.md :

| Action | Autonome | Nécessite approbation |
|--------|----------|----------------------|
| Lire / Rechercher | Toujours | — |
| Emails de routine | Sous le seuil | Au-dessus du seuil |
| Créer des factures | < 5 000 $ | > 5 000 $ |
| Supprimer quoi que ce soit | Jamais | Toujours |

### 6. Dry-Run

Toutes les opérations d'écriture : préparer → valider → exécuter. Pas de fire-and-forget.

---

## Auto-guérison

```
Auto-Stabilise (aux 10 min)
    ├── Lire health.json
    ├── Service down? → Restart (max 3/heure)
    ├── Plusieurs down? → Vérifier la cause racine d'abord, puis escalader
    └── Interdit : ne jamais restart SSH/systemd/Docker, ne jamais supprimer de données
```

Règles qui existent à cause d'incidents réels :

| Règle | Incident |
|-------|----------|
| Max 3 restarts/heure par service | Une boucle de crash a causé 2 083 restarts |
| Valider les ports avant assignation | Un conflit de port a fait tomber plusieurs services |
| Inclure sa propre IP dans le whitelist nginx | Une entrée manquante a causé 17h d'indisponibilité |
| Vérifier les dépendances après rebuild de container | Une bibliothèque manquante a cassé la recherche pendant 6 jours |

---

## Stratégie de données

Deux couches, chacune servant un objectif différent :

| Couche | Objectif | Fréquence de mise à jour |
|--------|----------|--------------------------|
| Mémoire RAG | Historique des conversations, décisions, contexte | Horaire |
| Blueprint | Snapshot ERP (clients, finances, projets) | Hebdomadaire |

```
Mémoire RAG    → "Qu'est-ce qui s'est passé hier?"
Blueprint      → "Quel est l'état actuel du Client A?"
```

---

## Concept central : Validation adversaire

L'idée centrale derrière cette architecture : **deux agents dans une arène**. Chaque action significative passe par une boucle défi-réponse où un agent propose et un autre valide.

Emprunté aux réseaux adversaires (GANs) — mais appliqué aux opérations business au lieu de la génération d'images. Le « générateur » propose des actions. Le « discriminateur » les vérifie.

### Fonctionnement

```
┌─────────────────────────────────────────────────────────────┐
│                   BOUCLE ADVERSAIRE                          │
│                                                              │
│   ┌────────────┐         ┌────────────┐                     │
│   │  PROPOSEUR  │ ──────→ │ VALIDATEUR  │                    │
│   │  (Worker)   │ ←────── │ (Réviseur)  │                    │
│   │             │ accepter │             │                    │
│   │  Génère     │ rejeter  │  Questionne │                    │
│   │  l'action   │ réviser  │  vérifie    │                    │
│   └────────────┘         └────────────┘                     │
│         │                       │                            │
│         ▼                       ▼                            │
│   "Créer facture           "Montant correspond au bon        │
│    de 4 200 $"              de travail? Client actif?        │
│                              Conditions correctes?"          │
│                                                              │
│   Exécute seulement si LES DEUX agents sont d'accord.       │
└─────────────────────────────────────────────────────────────┘
```

### Les deux systèmes comme adversaires

**Master Control** (couche agents) propose des actions basées sur les tâches, la connaissance du domaine et les règles d'affaires. **Master Commander** (couche infrastructure) valide la faisabilité, vérifie la santé système et applique les contraintes.

Aucun des deux systèmes ne fait aveuglément confiance à l'autre :

| Le proposeur dit | Le validateur vérifie |
|-----------------|----------------------|
| « Envoyer la facture au client » | Client existe? Montant correct? Pas déjà envoyée? |
| « Redémarrer le service X » | Max restarts atteint? Autres services affectés? |
| « Planifier une inspection » | Conflit de calendrier? Temps de déplacement réaliste? |
| « Envoyer un courriel au client pour paiement en retard » | Bon contact? Niveau d'escalade approprié? |

### Pourquoi c'est important

Les systèmes à agent unique échouent en silence. L'agent fait une erreur avec confiance et personne ne la rattrape. Avec la validation adversaire :

- **Les erreurs sont attrapées avant l'exécution** — le validateur pose les questions que le proposeur a oubliées
- **La confiance est méritée, pas présumée** — les deux agents doivent être d'accord
- **L'escalade est naturelle** — désaccord entre agents = demander à un humain
- **Les règles de domaine sont appliquées structurellement** — pas juste « espérées » via le prompting

### Niveaux de validation adversaire

```
Niveau 0 : Pas de validation     → L'agent agit seul (dangereux)
Niveau 1 : Auto-vérification     → L'agent révise sa propre sortie (faible)
Niveau 2 : Validation par pair   → Un second agent valide (cette architecture)
Niveau 3 : Humain dans la boucle → Les désaccords escaladent à l'opérateur
```

Cette architecture opère au Niveau 2 par défaut, avec escalade automatique au Niveau 3 quand les deux agents sont en désaccord.

---

## Démo

Une démo autonome est incluse dans le répertoire `demo/`. Elle fait tourner un Master Control Commander minimal sur votre machine locale — aucun service externe requis (sauf une clé API Claude).

### Ce que la démo inclut

| Composant | Fichier | Rôle |
|-----------|---------|------|
| Courtier de tâches | `task_broker.py` | File de tâches SQLite avec API REST |
| Serveur MCP simulé | `mock_mcp_server.py` | Outils de domaine simulés (bâtiments, inspections, clients) |
| Moniteur de santé | `health_monitor.py` | Vérifie les services, écrit health.json |
| Worker | `demo_worker.py` | Agent autonome : poll les tâches, appelle Claude, utilise les outils |
| Lanceur | `start_demo.sh` | Démarre tout dans le bon ordre |

### Démarrage rapide

```bash
git clone https://github.com/jlacerte/master-control-commander.git
cd master-control-commander/demo

# Configurer la clé API
cp .env.example .env
# Modifier .env et ajouter votre ANTHROPIC_API_KEY

# Installer et exécuter
pip install -r requirements.txt
./start_demo.sh
```

La démo initialise 3 tâches exemples (résumé d'inspection, suivis en retard, estimation de retrofit). Le worker les récupère, appelle Claude avec les outils simulés et produit des résultats.

### Exigences matérielles

| Configuration | RAM | Fonctionne? |
|---------------|-----|-------------|
| N'importe quel laptop moderne | 4+ Go | Oui — la démo utilise l'API seulement |
| VPS (4 CPU, 8 Go) | 8 Go | Oui — cible de production |

La démo nécessite Python 3.11+ et une clé API Claude. Pas de GPU requis.

### Quoi observer

1. **Pattern Guardian** — Le worker vérifie health.json avant chaque cycle de polling
2. **Cycle de vie des tâches** — Les tâches progressent : `todo → doing → done` (ou `→ review` en cas d'échec)
3. **Boucle d'utilisation d'outils** — Claude appelle les outils MCP simulés, traite les résultats, produit une sortie
4. **Disjoncteur** — Si une tâche échoue 3 fois, elle passe à `review` au lieu de réessayer

### Ajouter vos propres tâches

Pendant que la démo tourne :

```bash
curl -X POST http://localhost:8090/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Lister tous les bâtiments avec systèmes secs", "description": "Interroger la base de données et lister les bâtiments qui utilisent des systèmes à tuyauterie sèche."}'
```

---

## Déploiement en production

Pour un déploiement réel (pas la démo) :

1. **Déployer un serveur MCP** pour votre API la plus utilisée
2. **Créer un worker** utilisant la boucle de worker universelle
3. **Configurer le monitoring de santé** (cron + JSON)
4. **Ajouter le courtier de tâches** (Supabase gratuit ou SQLite)
5. **Connecter une interface de chat** (Slack Socket Mode ou équivalent)

### Trajectoire de montée en charge

```
Semaine 1 : 1 serveur MCP + 1 worker + vérification de santé
Semaine 2 : Ajouter 2-3 serveurs MCP supplémentaires
Semaine 3 : Second worker (rôle de validateur adversaire)
Semaine 4 : Auto-stabilisation + mémoire RAG
Mois 2 :   Automatisation Blueprint + boucles adversaires sur les chemins critiques
```

Tout tourne sur un seul VPS (4 CPU, 8 Go RAM, 20-50 $/mois). Systemd gère les services. Cron gère la planification. Pas de Kubernetes nécessaire.

---

## Secteurs d'application

Fonctionne pour les entreprises avec des flux de travail opérationnels répétitifs, des intégrations avec des systèmes externes et des connaissances spécifiques au domaine :

CVAC, plomberie, électricité, protection incendie, gestion immobilière, inspections d'assurance, maintenance d'équipement, gestion de construction.

---

## Leçons tirées de la production

1. **Deux agents sont plus intelligents qu'un.** La validation adversaire attrape les erreurs que l'auto-révision manque.
2. **CLAUDE.md est le produit.** Les instructions de domaine et les règles d'autonomie comptent plus que l'architecture.
3. **L'auto-guérison sauve à 3h du matin.** Disjoncteurs + auto-restart = dormir pendant que les problèmes se règlent.
4. **L'abstraction MCP est nécessaire.** Des agents sur des API brutes mènent à des boucles de retry et des problèmes OAuth.
5. **L'autonomie explicite bat le jugement du modèle.** Définir ce que les agents peuvent et ne peuvent pas faire.
6. **Un seul VPS suffit.** Résister à la sur-ingénierie à cette échelle.
7. **La santé avant les fonctionnalités.** Ne jamais déployer quand les services existants sont dégradés.
8. **Désaccord = escalade.** Quand les agents ne sont pas d'accord, un humain décide. C'est une fonctionnalité.

---

## Licence

MIT. Voir [LICENSE](LICENSE).

---

*Construit avec [Claude Code](https://claude.ai/code) + [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)*
