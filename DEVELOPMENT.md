# Guide de développement — ChantePaFo

Guide complet pour bosser sur ChantePaFo : setup, workflow, conventions, outils.

---

## Table des matières

1. [Prérequis](#prérequis)
2. [Setup initial](#setup-initial)
3. [Lancer en local](#lancer-en-local)
4. [Structure du projet](#structure-du-projet)
5. [Workflow de développement](#workflow-de-développement)
6. [Conventions de commit](#conventions-de-commit)
7. [Écrire des tests](#écrire-des-tests)
8. [Qualité du code](#qualité-du-code)
9. [Debugging](#debugging)
10. [Déploiement](#déploiement)

---

## Prérequis

| Outil | Version minimum | Usage |
|-------|----------------|-------|
| **Python** | 3.12+ | Backend |
| **uv** | latest | Gestion des deps Python |
| **Node.js** | 20+ | Frontend |
| **npm** | 10+ | Gestion des deps JS |
| **Docker** | 24+ | Redis + PostgreSQL en dev |
| **Git** | 2.40+ | VCS |

### Installation des outils

```bash
# uv (macOS / Linux / WSL)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Node via nvm (recommandé)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 20

# Docker Desktop : https://docker.com/products/docker-desktop
```

---

## Setup initial

```bash
# 1. Cloner le repo
git clone https://github.com/<ton-user>/ChantePaFo.git
cd ChantePaFo

# 2. Services (Redis + PostgreSQL)
docker compose up -d

# 3. Backend
cd backend
uv sync --all-extras      # installe toutes les deps (prod + dev)
cd ..

# 4. Frontend
cd frontend
npm install               # installe les deps + déclenche husky init
cd ..
```

À ce stade, Husky doit avoir installé les hooks pre-commit. Vérifie avec :
```bash
ls frontend/.husky/
# Doit contenir : _/, commit-msg, pre-commit
```

### Variables d'environnement

Crée un fichier `.env` à la racine (jamais committé) :

```env
# Backend
CHANTEPAFO_DATABASE_URL=postgresql+asyncpg://chantepafo:chantepafo_dev@localhost:5432/chantepafo
CHANTEPAFO_REDIS_URL=redis://localhost:6379
CHANTEPAFO_SECRET_KEY=dev-secret-change-me-in-prod
CHANTEPAFO_CORS_ORIGINS=["http://localhost:5173"]

# Frontend (prefixe VITE_ obligatoire pour être exposé au client)
VITE_API_URL=http://localhost:8000
VITE_APP_VERSION=dev
```

---

## Lancer en local

Besoin de **3 terminaux** :

**Terminal 1 — Services Docker**
```bash
docker compose up
```

**Terminal 2 — Backend**
```bash
cd backend
uv run uvicorn app.main:socket_app --reload --port 8000
```
→ API disponible sur `http://localhost:8000`
→ Docs auto : `http://localhost:8000/docs`

**Terminal 3 — Frontend**
```bash
cd frontend
npm run dev
```
→ App disponible sur `http://localhost:5173`

### Vérifier que tout marche

1. Ouvre `http://localhost:5173`
2. Entre un pseudo, clique "Créer une room"
3. Un code type `FUNK42` apparaît
4. Ouvre un second onglet, entre le code et un autre pseudo
5. Les deux onglets doivent se voir dans le lobby

---

## Structure du projet

```
ChantePaFo/
├── backend/                  # FastAPI + Socket.IO
│   ├── app/
│   │   ├── main.py           # Entry point (FastAPI + Socket.IO mount)
│   │   ├── config.py         # Settings (env vars via pydantic-settings)
│   │   ├── database.py       # SQLAlchemy + Redis connections
│   │   ├── models.py         # Modèles SQLAlchemy
│   │   ├── auth/             # Authentication (register, login, JWT)
│   │   ├── rooms/            # Gestion des rooms (Redis, codegen)
│   │   ├── music/            # Client Deezer API
│   │   ├── game/             # Game engine + modes de jeu
│   │   │   ├── engine.py     # GameMode ABC + registry
│   │   │   ├── fuzzy.py      # Fuzzy matching
│   │   │   ├── scoring.py    # Calcul des scores
│   │   │   ├── awards.py     # Wall of Shame & Fame
│   │   │   ├── blindtest.py  # Mode Blindtest
│   │   │   ├── karaoke.py    # Mode Karaoké Mystère
│   │   │   └── telephone.py  # Mode Téléphone Arabe
│   │   ├── ambiance/         # Moteur d'ambiance (genre → palette)
│   │   ├── reactions/        # Réactions emoji + soundboard
│   │   └── sockets/          # Event handlers Socket.IO
│   ├── tests/                # Tests pytest
│   └── pyproject.toml        # Config uv + deps
│
├── frontend/                 # Vue 3 SPA
│   ├── src/
│   │   ├── main.ts           # Entry point (Vue + Pinia + Router)
│   │   ├── App.vue           # Shell (ambiance glows + router-view)
│   │   ├── router/           # Vue Router config
│   │   ├── stores/           # Pinia stores (auth, room, game, ambiance)
│   │   ├── composables/      # Logique réutilisable (useSocket, useAudio...)
│   │   ├── views/            # Vues principales (Home, Lobby, Game)
│   │   ├── components/       # Composants UI
│   │   ├── types/            # Types TypeScript partagés
│   │   └── assets/           # Design system (tokens, global, animations)
│   ├── tests/                # Tests vitest
│   └── package.json
│
├── docs/                     # Documentation
├── .github/workflows/        # CI/CD GitHub Actions
├── docker-compose.yml        # Services dev (Redis + PostgreSQL)
├── Dockerfile                # Image production backend
└── README.md
```

### Où mettre un nouveau fichier ?

| Je veux... | Je le mets dans... |
|-----------|-------------------|
| Ajouter un mode de jeu | `backend/app/game/<mode>.py` + `tests/test_<mode>.py` |
| Ajouter un endpoint REST | `backend/app/<domain>/router.py` |
| Ajouter un event Socket.IO | `backend/app/sockets/handlers.py` |
| Ajouter un composant réutilisable | `frontend/src/components/<Name>.vue` |
| Ajouter une vue (page) | `frontend/src/views/<Name>View.vue` + route dans `router/index.ts` |
| Ajouter de la logique réutilisable | `frontend/src/composables/use<Name>.ts` |
| Ajouter un style global | `frontend/src/assets/global.css` |
| Ajouter une variable CSS | `frontend/src/assets/tokens.css` |

---

## Workflow de développement

### Stratégie de branches

```
feature/my-feature ──push──→ dev ──PR──→ main
                               │
                               └── déploie staging
                                            │
                                            └── déploie prod (via PR)
```

- **`feature/<nom>`** — branche de travail, part de `dev`
- **`dev`** — intégration, auto-deploy sur staging
- **`main`** — production, reçoit uniquement des PRs depuis `dev`

### Workflow typique

```bash
# 1. Partir de dev à jour
git checkout dev
git pull origin dev

# 2. Créer une branche feature
git checkout -b feature/karaoke-progressive

# 3. Développer (TDD !)
# - Écrire le test qui échoue
# - Implémenter
# - Vérifier que le test passe
# - Commit (pre-commit hook se déclenche automatiquement)

git add backend/app/game/karaoke.py backend/tests/test_karaoke.py
git commit -m "feat: add progressive mode to karaoke"

# 4. Push
git push -u origin feature/karaoke-progressive

# 5. Ouvrir une PR vers dev sur GitHub
gh pr create --base dev --title "feat: add progressive mode to karaoke"

# 6. Attendre que la CI passe + review
# 7. Merger → auto-deploy staging
# 8. Plus tard, PR dev → main pour déploiement prod
```

---

## Conventions de commit

**Conventional Commits obligatoires** — validé par `commitlint` en pre-commit. Format :

```
<type>: <description en minuscules, impératif, sans point final>
```

| Type | Version bump | Quand l'utiliser | Exemple |
|------|-------------|------------------|---------|
| `feat:` | **minor** (0.X.0) | Nouvelle fonctionnalité | `feat: add karaoke progressive mode` |
| `fix:` | **patch** (0.0.X) | Correction de bug | `fix: fuzzy matching on accented chars` |
| `feat!:` | **major** (X.0.0) | Breaking change | `feat!: redesign scoring API` |
| `docs:` | — | Documentation seulement | `docs: update API endpoints` |
| `style:` | — | Formatage, pas de code change | `style: reformat with ruff` |
| `refactor:` | — | Refacto sans changement fonctionnel | `refactor: extract scoring into module` |
| `test:` | — | Ajout/modif de tests | `test: add fuzzy edge cases` |
| `chore:` | — | Build, CI, tooling, deps | `chore: update dependencies` |
| `perf:` | — | Amélioration de performance | `perf: batch WebSocket events` |

### Breaking changes

Pour un breaking change, utilise `!` ou `BREAKING CHANGE:` dans le footer :

```
feat!: redesign room system

BREAKING CHANGE: l'API /rooms a changé de format.
Les clients existants devront migrer.
```

### Messages de commit

- **En minuscules** : `feat: add X`, pas `feat: Add X`
- **Impératif** : `add`, pas `added` ou `adds`
- **Pas de point final**
- **Concis** : une ligne, < 100 caractères pour le titre
- **Détails dans le body** si besoin (optionnel)

---

## Écrire des tests

**TDD est obligatoire** pour tout nouveau code métier (game modes, fuzzy matching, scoring, awards).

### Backend — pytest

**Structure** : chaque module `backend/app/<domain>/<file>.py` a son `backend/tests/test_<file>.py`.

**Fixtures disponibles** (dans `conftest.py`) :
- `db_session` — session SQLAlchemy sur une DB SQLite de test
- `fake_redis` — instance Redis mockée
- `client` — AsyncClient FastAPI avec les dépendances overridées

**Cycle TDD** :

```bash
# 1. Écrire le test qui échoue
vim backend/tests/test_fuzzy.py

# 2. Lancer le test — doit FAIL
cd backend && uv run pytest tests/test_fuzzy.py -v
# Expected: FAIL (module not found, or assertion error)

# 3. Implémenter le minimum
vim backend/app/game/fuzzy.py

# 4. Lancer à nouveau — doit PASS
cd backend && uv run pytest tests/test_fuzzy.py -v

# 5. Refactor si besoin, vérifier que ça passe toujours
```

**Exemple de test** :

```python
# backend/tests/test_fuzzy.py
from app.game.fuzzy import fuzzy_match

def test_typo_match_title():
    result = fuzzy_match("trhiller", "Thriller", "Michael Jackson")
    assert result["title_match"] is True

def test_accented_match():
    result = fuzzy_match("desapcito", "Despacito", "Luis Fonsi")
    assert result["title_match"] is True

def test_no_match():
    result = fuzzy_match("bananas", "Thriller", "Michael Jackson")
    assert result["title_match"] is False
    assert result["artist_match"] is False
```

**Async tests** :

```python
import pytest

@pytest.mark.asyncio
async def test_create_room(room_service):
    room = await room_service.create_room(host_id="h1", host_name="Alice")
    assert room["code"]
```

**Mocker Deezer API** :

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_search_tracks(deezer):
    mock_response = {"data": [{"id": 1, "title": "Test", ...}]}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.json.return_value = mock_response
        tracks = await deezer.search("test")
        assert len(tracks) == 1
```

### Frontend — vitest + Vue Test Utils

**Structure** : tests dans `frontend/tests/` (miroir de `src/`).

```typescript
// frontend/tests/composables/useRecorder.test.ts
import { describe, it, expect, vi } from 'vitest'
import { useRecorder } from '@/composables/useRecorder'

describe('useRecorder', () => {
  it('starts recording when startRecording called', async () => {
    // Mock browser API
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue(new MediaStream()),
    } as any

    const { isRecording, startRecording } = useRecorder()
    await startRecording()
    expect(isRecording.value).toBe(true)
  })
})
```

**Tester un composant** :

```typescript
import { mount } from '@vue/test-utils'
import AnswerInput from '@/components/AnswerInput.vue'

it('emits submit on Enter', async () => {
  const wrapper = mount(AnswerInput)
  await wrapper.find('input').setValue('thriller')
  await wrapper.find('input').trigger('keydown.enter')
  expect(wrapper.emitted('submit')).toBeTruthy()
  expect(wrapper.emitted('submit')![0]).toEqual(['thriller'])
})
```

### Lancer les tests

```bash
# Backend - tous les tests
cd backend && uv run pytest tests/ -v

# Backend - un fichier
cd backend && uv run pytest tests/test_fuzzy.py -v

# Backend - un test précis
cd backend && uv run pytest tests/test_fuzzy.py::test_typo_match_title -v

# Backend - avec couverture
cd backend && uv run pytest --cov=app --cov-report=term-missing

# Frontend - tous les tests
cd frontend && npm run test

# Frontend - watch mode
cd frontend && npm run test -- --watch

# Frontend - avec couverture
cd frontend && npm run test -- --coverage
```

### Quoi tester

✅ **À tester** :
- Logique métier (fuzzy matching, scoring, awards, game modes)
- Endpoints API (happy path + erreurs)
- Composables avec logique (useRecorder, useAudio)
- Composants interactifs (AnswerInput, Countdown)

❌ **Pas besoin de tester** :
- Wrappers triviaux autour de `fetch`
- Composants purement visuels sans logique
- Getters Pinia qui retournent juste un état
- Types TypeScript (le compilateur le fait)

---

## Qualité du code

### Outils automatiques (pre-commit)

Quand tu fais `git commit`, ces outils tournent automatiquement :

| Outil | Action |
|-------|--------|
| **ruff** | Lint + format Python (fix auto) |
| **eslint** | Lint TypeScript/Vue (fix auto) |
| **prettier** | Format TS/Vue/CSS/JSON/MD (fix auto) |
| **commitlint** | Valide le format du message de commit |

Si un outil échoue, le commit est bloqué. Corrige les erreurs et re-commit.

### Outils manuels

```bash
# Backend - type checking strict
cd backend && uv run mypy app/

# Backend - lint sans fix
cd backend && uv run ruff check .

# Backend - format check
cd backend && uv run ruff format --check .

# Frontend - type checking
cd frontend && npm run type-check

# Frontend - lint
cd frontend && npx eslint src/ --max-warnings 0
```

### SonarQube

À chaque PR, **SonarQube** (via `sonar-scanner` en CI) analyse le code et poste un rapport avec :
- **Quality gate** (pass/fail)
- **Code smells** (odeurs de code, complexité cyclomatique)
- **Bugs** (problèmes détectés)
- **Vulnerabilities** (failles de sécurité)
- **Coverage** (couverture des tests, alimentée par pytest-cov + vitest coverage)
- **Duplication** (code dupliqué)

SonarQube peut être auto-hébergé (Docker) ou utiliser SonarCloud (la version hostée gratuite pour open source) — à choisir selon tes besoins de privacy et ton budget.

**Règles** :
- La quality gate doit passer pour merger
- Couverture minimum : **70%**
- 0 bug critique, 0 vulnerability
- Code smells "critical" : 0

### Dependabot

Chaque semaine, Dependabot ouvre des PRs automatiques pour les deps :
- Python (`pyproject.toml`)
- npm (`package.json`)
- GitHub Actions (workflows)

Review et merge si la CI passe.

---

## Debugging

### Backend

**Logs** : utilise `print()` en dev, `logging` pour prod.

**Breakpoints** : Python natif `breakpoint()` ou VSCode debugger.

**Inspecter Redis** :
```bash
docker exec -it chantepafo-redis-1 redis-cli
> KEYS room:*
> GET room:FUNK42
```

**Inspecter PostgreSQL** :
```bash
docker exec -it chantepafo-postgres-1 psql -U chantepafo -d chantepafo
chantepafo=# \dt
chantepafo=# SELECT * FROM users;
```

### Frontend

**Vue DevTools** : extension navigateur obligatoire pour debug les stores, composants, events.

**Console** : `console.log()` dans `<script setup>`, visible dans la console navigateur.

**Socket.IO debug** :
```typescript
// Active les logs Socket.IO dans le navigateur
localStorage.debug = 'socket.io-client:*'
```

**Network** : onglet Network du navigateur, filter sur `WS` pour voir les frames WebSocket.

---

## Déploiement

Le déploiement est **automatique** via GitHub Actions :

| Branche | Trigger | Action |
|---------|---------|--------|
| `feature/*` | Push | CI (lint + tests + build) |
| `dev` | Push (via PR) | CI + auto-deploy staging |
| `main` | Push (via PR depuis dev) | CI + semantic-release + auto-deploy prod |

### Staging

- **Frontend** : Vercel preview `chantepafo-staging.vercel.app`
- **Backend** : Railway `chantepafo-backend-staging.railway.app`

### Production

- **Frontend** : Vercel prod `chantepafo.com`
- **Backend** : Railway prod `api.chantepafo.com`
- **Version** : tag git automatique via semantic-release (ex: `v1.2.3`)
- **Changelog** : généré dans `CHANGELOG.md` + GitHub Releases

### Secrets GitHub (à configurer dans Settings > Secrets)

| Secret | Source |
|--------|--------|
| `RAILWAY_TOKEN` | Railway dashboard > Account > Tokens |
| `VERCEL_TOKEN` | Vercel dashboard > Settings > Tokens |
| `VERCEL_ORG_ID` | `vercel link` dans le dossier frontend |
| `VERCEL_PROJECT_ID` | `vercel link` dans le dossier frontend |
| `SONAR_TOKEN` | SonarQube > My Account > Security |

### Rollback

Si une release prod pose problème :

```bash
# Option 1 : revert du commit + push sur main
git revert <commit-sha>
git push origin main
# → CI re-déploie automatiquement

# Option 2 : redeploy manuel sur Railway/Vercel
# Aller dans le dashboard de la plateforme et redéployer un build antérieur
```

---

## Ressources

- **Spec MVP** : `docs/superpowers/specs/2026-04-04-chantepafo-mvp-design.md`
- **Spec UX** : `docs/superpowers/specs/2026-04-04-chantepafo-frontend-ux-design.md`
- **Plan implémentation** : `docs/superpowers/plans/2026-04-04-chantepafo-mvp.md`
- **Deezer API** : https://developers.deezer.com/api
- **Socket.IO** : https://socket.io/docs/v4/
- **FastAPI** : https://fastapi.tiangolo.com
- **Vue 3** : https://vuejs.org/guide/
- **uv** : https://docs.astral.sh/uv/
