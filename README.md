# ChantePaFo

**The musical party game for friends.**

Blindtest, mystery karaoke, musical telephone game, and much more — all with a dynamic light ambiance system that turns your living room (or your screen) into a concert.

> [See the visual preview](https://chantepafo.github.io/) (static page of the planned design)

---

## Concept

ChantePaFo is a **multiplayer musical mini-game hub** designed for nights with friends. The idea: a host creates a room, everyone joins with a code from their phone or PC, and the party begins.

- **4 to 10 players** at once
- **In-person** (living room, pizza night) or **remote** (Discord, video call)
- **Zero friction**: a code, a nickname, no mandatory account
- **Silliness is a feature**: mechanics encourage singing off-key, bad drawings, mistakes. The fun comes from the offbeat moments, not performance.

**Inspired by:** Skribbl.io, Gartic Phone, Jackbox Party Packs, WhatTheTune, SongPop.

---

## Game modes

### MVP (Phase 1)

| Mode | Description |
|------|-------------|
| **Classic Blindtest** | A clip plays, guess the title and/or artist as fast as possible. Typo-tolerant input (fuzzy matching), multiple attempts allowed. Speed-based scoring. |
| **Mystery Karaoke** | Everyone listens to a clip, then each player records themselves singing it from memory (30s). Recordings are played anonymously and others must guess the song. **Classic** mode (constant difficulty) or **progressive** (growing constraints: humming, onomatopoeia, forced voice, whispering...). |
| **Musical Telephone Game** | The signature mode, inspired by Gartic Phone. Everyone plays simultaneously. Each player listens to a different clip and sings it. The next player listens to the singing and writes the title. The next reads the title and sings what they imagine. And so on. At the end, each chain is unrolled step by step — the progressive deformation is the spectacle. |

### Future modes (by complexity)

| Phase | Mode | Description |
|-------|------|-------------|
| 2 | **Reverse Blindtest** | The title is shown, find the correct clip among 5 altered versions (slowed, sped up, pitch shifted). |
| 2 | **Era Map** | Place the release year on a timeline. No need to know the title. |
| 3 | **Progressive Instruments** | Tracks are added one by one (drums, bass, guitar, vocals). Buzz as soon as you recognize it. |
| 3 | **Category Battle** | Each player picks a music category to trap others. Tactical dimension. |
| 3 | **Sonic Witness** | One "witness" player hears everything, others only get fragments. The witness gives emoji-only clues. |
| 3 | **Musical Legacy** | Each correct answer = an audio handicap for an opponent (echo, slowed, reversed). Chaos escalates. |
| 4 | **Composer Mode** | Reproduce the melody on a mini virtual keyboard after listening. |
| 4 | **Freestyle Karaoke** | Sing a known song over a forced instrumental (funk, metal, bossa...). Others judge the result. |
| 4 | **Musical Drawing Battle** | Draw the song instead of writing it. Others guess from the drawing. |
| 5 | **Human Orchestra** | Each player reproduces a track (drums, bass, vocals...) with their voice. Everything is layered. Unintentional masterpiece guaranteed. |

---

## Light ambiance system

Every connected screen (phone or PC) becomes a **light spot**. Colors and effects change in real time based on the current music genre and pulse to the beat.

| Genre | Ambiance |
|-------|----------|
| Rock/Metal | Dark red, aggressive flashes |
| Disco/Funk | Gold, purple, disco ball |
| Pop | Pastel neon, soft waves |
| Rap/Hip-hop | Purple, neon green, heavy pulse |
| Electro | Cyan, magenta, strobe |
| Jazz/Soul | Amber, midnight blue, warm |
| 80s | Pink, cyan, purple, synthwave |

Effects also adapt to **key moments**: build-up during countdown, flash on correct answer, stage spotlight during recording, burst of light during reveal.

---

## Wall of Shame & Fame

At the end of each game, **offbeat awards** are automatically handed out:

| Award | Description |
|-------|-------------|
| The Maestro | Best overall score |
| Tin Ear | Worst score |
| Human Shazam | Fastest answer |
| The Poet | The most absurd answer (displayed as-is) |
| The Ghost | Most rounds without answering |
| The Raging One | Most failed attempts in a single round |
| The One Hit Wonder | Only one correct answer, but first |

Each mode adds its own awards (Golden Voice, Weakest Link, The Scrambler...).

---

## Reactions and Soundboard

During reveals and games, players can:

- **React live** with emojis (😂 👏 💀 🔥) that appear on all screens
- **Soundboard**: sound buttons (applause, boos, drumroll, buzzer)
- **Vote** after each Telephone Game chain (funniest, best drift, weakest link)

---

## How it works

```
1. Host creates a room          →  Code: FUNK42
2. Friends join                 →  chantepafo.com/FUNK42 + nickname
3. Host picks the mode          →  Blindtest, Karaoke, Telephone Game
4. Host selects genres          →  Pop, Rock, Rap, Electro, All...
5. Launch the party !
6. Chain modes without recreating the room
```

- **No mandatory account** to play (nickname is enough)
- **Optional account** for the host (keep stats, create rooms)
- **Works on phone AND PC** (responsive)
- **In-person or remote** (Discord/video call for voice chat)

---

## Tech stack

| Layer | Tech |
|-------|------|
| Frontend | Vue 3, TypeScript, Vite |
| Backend | Python 3.12, FastAPI, Socket.IO |
| Real-time | WebSocket via python-socketio / socket.io-client |
| Database | PostgreSQL (accounts, stats) + Redis (room state, real-time) |
| Music | Deezer API (30s previews, free) |
| Audio capture | Web Audio API + MediaRecorder (browser mic) |
| Ambiance | Web Audio API (FFT) + CSS Custom Properties |
| Package manager | uv (Python), npm (JS) |
| CI | GitHub Actions (lint + tests + build on every push) |
| CD | Vercel (frontend) + Railway (backend) |
| Code quality | SonarQube (quality gate), Dependabot (dep updates) |
| Versioning | semantic-release (auto version + changelog + GitHub Releases) |

### Design

- **Neon / Club** theme: dark background, vibrant glows, colors that shift with the music
- Typography: **Righteous** (titles, logo, awards) + **Fredoka** (UI, buttons, body)
- Animations: **dynamic** baseline, **over the top** on key moments (confetti, shake, exploding scores)
- CSS Custom Properties for the design system (no CSS framework)

---

## Quick start

```bash
# 1. Services (Redis + PostgreSQL)
docker compose up -d

# 2. Backend
cd backend
uv sync --all-extras
uv run uvicorn app.main:socket_app --reload --port 8000

# 3. Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

For the full dev guide, see [DEVELOPMENT.md](DEVELOPMENT.md).

---

## Roadmap

- [x] Design spec and implementation plan
- [ ] **Phase 1** — MVP (Blindtest + Mystery Karaoke + Telephone Game + Light Ambiance)
- [ ] **Phase 2** — Reverse Blindtest + Era Map
- [ ] **Phase 3** — Progressive Instruments + Category Battle + Sonic Witness + Musical Legacy
- [ ] **Phase 4** — Composer Mode + Freestyle Karaoke + Drawing Battle
- [ ] **Phase 5** — Human Orchestra
- [ ] **Cross-cutting** — Optional shared screen (TV), custom soundboard, monetization

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions (Conventional Commits required) and branching strategy (`feature/* → dev → main`).

---

## Status

In active development.
