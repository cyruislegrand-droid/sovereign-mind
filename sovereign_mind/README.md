# 🜂 Sovereign Mind · MENA Command

> *See the global event. Decode the hidden link. Act sovereign.*

A zero-cost, self-hosting geopolitical intelligence dashboard built around three sovereign personas:

| | Persona | Doctrine |
|---|---|---|
| 🇲🇦 | **The Atlas Strategist** (Morocco) | Patient, pragmatic positioning. Bridge between Africa, Europe, and the Atlantic. |
| 🇸🇦 | **The Visionary Architect** (KSA) | Ambitious diversification. Re-engineer the economy beyond hydrocarbons. |
| 🇦🇪 | **The Global Connector** (UAE) | Hyper-connected, capital-light, talent-magnet. The world's neutral switchboard. |

---

## Architecture

```
┌────────────────────────┐    ┌──────────────────────────┐    ┌────────────────────────┐
│  RSS feeds (global +   │    │  GitHub Actions (hourly) │    │  Streamlit cockpit     │
│  MENA) + Telegram      │───▶│  processor.py            │───▶│  app.py (reads         │
│  channels              │    │   • scrape ~100 articles │    │  data/data.json)       │
│                        │    │   • single Scout pass    │    │                        │
└────────────────────────┘    │   • write data.json      │    └────────────────────────┘
                              └──────────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────────┐
                              │  Llama-4-Scout-17B-16E   │
                              │  via Groq                │
                              │  10M-token context       │
                              │  ALL articles in one     │
                              │  pass → hidden links     │
                              └──────────────────────────┘
```

### Why "context-stuffing" works
Llama 4 Scout's 10M-token context window means the model sees **all 100 articles simultaneously**. The hidden-link detection isn't post-hoc clustering — it emerges from a single forward pass that can correlate, e.g., a US chip-export rule + a Korean shipyard fire + an ADNOC LNG deal in one shot. A traditional pipeline (per-article sentiment → cluster → recommend) cannot find these compound signals.

---

## Refresh architecture (two-tier)

| Layer | Cadence | Where | What it does |
|---|---|---|---|
| **Pipeline** | every 15 min | GitHub Actions | Scrapes feeds, runs Scout, commits `data/data.json` |
| **Cockpit** | every 3 min (default) | Browser | Re-reads `data.json`, busts the data cache, re-renders |

The cockpit auto-refreshes faster than the pipeline updates — that's intentional. The UI feels live (countdowns, fresh KPIs after each commit) without burning Actions minutes or Groq quota. Toggle / interval are in the sidebar; available steps: 1m / 2m / 3m / 5m / 10m / 15m. Disable the toggle for static viewing.

### Why not 3-min cron?
- GitHub Actions free tier = 2,000 min/mo. Hourly = ~24 hr/mo used. Every-3-min = ~1,440 hr/mo (impossible).
- `cron` in Actions is documented as best-effort; sub-5-min schedules are unreliable in practice.
- 480 commits/day to `data.json` would bloat git history.

If you genuinely need sub-minute pipeline refresh, run `processor.py` on a small VPS in a `while sleep` loop instead of Actions.

---

## Files

| File | Role |
|---|---|
| `app.py` | Streamlit cockpit — five tabs (Pulse, Butterfly Map, Hidden Links, Sovereign Lens, Decisions) |
| `processor.py` | Hourly pipeline — scrape, enrich via Scout, write `data/data.json` |
| `translations.py` | i18n dict (EN / FR / AR) + persona metadata |
| `requirements.txt` | All deps |
| `.streamlit/config.toml` | Base dark theme |
| `.github/workflows/refresh.yml` | Hourly GitHub Action |
| `data/data.json` | Latest enriched intelligence snapshot (committed by the bot) |

---

## Local development

```bash
# 1. clone & install
git clone <your-fork> sovereign-mind && cd sovereign-mind
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. populate data (optional — app falls back to seed data otherwise)
export GROQ_API_KEY=gsk_...
python processor.py

# 3. run the cockpit
streamlit run app.py
```

Open http://localhost:8501.

---

## Deployment (zero-cost path)

1. **Fork this repo** to your GitHub account.
2. Add repository secrets in *Settings → Secrets and variables → Actions*:
   - `GROQ_API_KEY` *(required)*
   - `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION` *(optional)*
3. The hourly Action will run `processor.py` and commit `data/data.json` back to the repo.
4. Deploy `app.py` to **Streamlit Community Cloud** (free) — point it at this repo. The app reads the committed JSON, so no runtime API key is required for the cockpit itself.

> Total infrastructure cost: $0. Groq's free tier covers ~24 hourly Scout calls/day comfortably.

---

## Personas customization

Each persona is defined in `translations.py::PERSONAS`. Edit the dict to:

- Re-color the UI per persona (`colors.primary`, `colors.glow`)
- Swap pillars / strategic priorities
- Translate the doctrine into another language (just add a key to the `names`/`doctrine` sub-dicts)

Scout prompts in `processor.py::SCOUT_SYSTEM` reference these pillars by name — keep them in sync.

---

## Multilingual / RTL

- Three languages out of the box: `en`, `fr`, `ar`.
- Selecting Arabic flips the entire UI to RTL via injected CSS (`direction: rtl`) and switches the body font stack to Noto Naskh + Reem Kufi.
- Add a fourth language by appending a key to every dict in `translations.py::TRANSLATIONS` plus an entry in `LANG_LABELS`.

---

## Caveats

- The seed data shipped in `data/data.json` is illustrative. The first cron run will overwrite it with live enrichment.
- RSS feeds occasionally rate-limit; `processor.py` uses tenacity retries but partial scrapes are normal.
- The Butterfly Map uses approximate geo centroids per ISO country code — refine `_geo_centroids()` in `app.py` if you need finer source coordinates.
- This is a *decision-support* tool, not an oracle. Always verify before acting.
