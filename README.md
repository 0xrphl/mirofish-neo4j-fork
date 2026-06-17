<div align="center">

![MiroFish Neo4j Fork](images/banner.png)

# MiroFish Neo4j Fork

**Multi-Agent AI Prediction Engine — Fully Self-Hosted with Neo4j**

[![Fork of MiroFish](https://img.shields.io/badge/Fork_of-MiroFish-DAA520?style=for-the-badge&logo=github)](https://github.com/666ghj/MiroFish)
[![Neo4j](https://img.shields.io/badge/Neo4j-Graph_DB-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-AGPL_3.0-red?style=for-the-badge)](https://github.com/666ghj/MiroFish/blob/main/LICENSE)

*A fork of [MiroFish](https://github.com/666ghj/MiroFish) that replaces **Zep Cloud** with **Neo4j** — no vendor lock-in, no cloud dependency, fully offline.*

</div>

---

## Why This Fork?

The original [MiroFish](https://github.com/666ghj/MiroFish) depends on **Zep Cloud** — a closed-source, cloud-hosted graph database. This fork replaces it with a local **Neo4j** instance:

| | Zep Cloud (Original) | Neo4j (This Fork) |
|---|---|---|
| **Hosting** | Cloud-only | Local Docker container |
| **Cost** | Free tier limits | Completely free |
| **Privacy** | Data sent to cloud | Data stays on your machine |
| **Offline** | Requires internet | Works fully offline |
| **Open Source** | Proprietary | Neo4j Community Edition |
| **Query Language** | Custom API | Cypher (industry standard) |
| **Browser UI** | Limited | Full Neo4j Browser at `:7474` |

---

## Screenshots

### MiroFish Homepage

![MiroFish Homepage](images/homepage.png)

> MiroFish prediction engine — upload documents and build knowledge graphs

### Knowledge Graph Building

![Graph Build](images/graph-build.png)

> Ontology generation + graph construction from uploaded documents

### Full-Screen Knowledge Graph

![Full Screen Graph](images/graph-fullscreen.png)

> Interactive graph visualization with entities and relationships

### Agent Persona Generation

![Agent Personas](images/agent-personas-graph.png)

![Agent Personas Dual View](images/agent-personas-dual.png)

> AI-generated agent personas from the knowledge graph

### Simulation Setup

![Simulation Setup](images/simulation-setup.png)

> Custom agent configuration before running the simulation

### Running Simulation

![Running Simulation](images/simulation-running.png)

> Parallel multi-agent simulation with real-time interaction view

### Final Report & Agent Chat

![Final Report](images/final-report.png)

> Comprehensive report with graph view and interactive agent Q&A

---

## Quick Start

### Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- An [OpenAI API key](https://platform.openai.com/api-keys) (for LLM reasoning)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env — add your OpenAI API key
```

### 2. Start All Services

```bash
docker compose up -d
```

### 3. Open the UI

| Service | URL | Credentials |
|---------|-----|-------------|
| **MiroFish UI** | http://localhost:3000 | — |
| **MiroFish API** | http://localhost:5001 | — |
| **Neo4j Browser** | http://localhost:7474 | `neo4j` / `mirofish2026` |
| **ChromaDB** | http://localhost:8000 | — |
| **Whisper ASR** | http://localhost:9000 | — |

---

## How It Works

All Neo4j patches are **automatically applied** on every `docker compose up` via a custom entrypoint script. No manual steps needed.

```
docker compose up -d
         │
         ▼
  ┌──────────────────┐
  │  patches/         │  Auto-applied at startup:
  │  entrypoint.sh    │  • graph_builder.py → Neo4j
  │                   │  • zep_entity_reader.py → Neo4j
  │                   │  • zep_tools.py → Neo4j monkey-patch
  │                   │  • config.py → skip Zep validation
  └──────┬───────────┘
         ▼
  ┌──────────────┐  ┌────────────┐  ┌───────────┐  ┌─────────┐
  │  MiroFish    │  │   Neo4j    │  │ ChromaDB  │  │ Whisper │
  │  :3000/:5001 │  │ :7474/:7687│  │  :8000    │  │  :9000  │
  └──────────────┘  └────────────┘  └───────────┘  └─────────┘
```

---

## Project Structure

```
.
├── .env.example              # Environment template (copy to .env)
├── .gitignore                # Keeps secrets and data out of git
├── docker-compose.yml        # All services + auto-patching entrypoint
├── README.md
│
├── images/                   # Screenshots for documentation
│
└── patches/                  # Neo4j patches (auto-applied on startup)
    ├── entrypoint.sh               # Startup script that applies all patches
    ├── neo4j_graph_builder.py      # Replaces Zep graph builder with Neo4j
    ├── neo4j_entity_reader.py      # Replaces Zep entity reader with Neo4j
    ├── neo4j_graph_api.py          # Flask blueprint for /api/neo4j/ endpoints
    └── patch_zep_tools.py          # Monkey-patches ZepToolsService → Neo4j
```

---

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `LLM_API_KEY` | OpenAI API key (or compatible) | Yes |
| `LLM_BASE_URL` | LLM API base URL | Yes |
| `LLM_MODEL_NAME` | Model name (e.g. `gpt-4o`) | Yes |
| `ZEP_API_KEY` | Placeholder (needed by original image to start) | Yes* |
| `NEO4J_URI` | Neo4j Bolt URI | No (default in compose) |
| `NEO4J_PASSWORD` | Neo4j password | No (default: `mirofish2026`) |

---

## What's Working

| Feature | Status |
|---------|--------|
| MiroFish UI at localhost:3000 | ✅ Working |
| LLM-powered ontology generation | ✅ Working |
| Knowledge graph building → **Neo4j** | ✅ Working |
| Neo4j Browser at localhost:7474 | ✅ Working |
| ChromaDB vector embeddings | ✅ Working |
| Whisper audio transcription | ✅ Working |
| Entity reading from Neo4j | ✅ Working |
| Agent persona generation | ✅ Working |
| Multi-agent simulation | ✅ Working |
| Final report + interactive Q&A | ✅ Working |
| Auto-patching on `docker compose up` | ✅ Working |

---

## Industry Applications: Predictive Markets & Agentic Consensus

MiroFish Neo4j Fork is not just a research tool — it is a **production-grade infrastructure** for building intelligent prediction systems. The combination of multi-agent simulation, knowledge graphs, and parallel consensus makes it uniquely suited for high-stakes forecasting environments.

### 🎯 Predictive Markets & Autonomous Trading

This engine can serve as the **decision-making backbone** for prediction market platforms like [Polymarket](https://polymarket.com/), [Kalshi](https://kalshi.com/), and decentralized forecasting protocols:

- **Autonomous Market Agents** — Deploy specialized AI agents that independently research, reason, and form probabilistic forecasts on real-world events (elections, macro indicators, geopolitical outcomes).
- **Bot Trading Pipelines** — Pipe agent consensus outputs directly into trading strategies. Each agent acts as an independent analyst; the aggregated signal drives position sizing and market entry/exit.
- **Event-Driven Forecasting** — Upload breaking news, earnings reports, or policy documents. The system builds a knowledge graph in real time and spawns agents to evaluate downstream effects — enabling rapid, evidence-based market positioning.

### 🤖 Agentic Parallel Consensus

Unlike single-model inference, MiroFish runs **parallel multi-agent simulations** where each agent operates with a distinct persona, knowledge base, and reasoning strategy:

- **Diverse Cognitive Profiles** — Agents are generated from the knowledge graph with unique expertise, biases, and analytical lenses. This mirrors ensemble methods in ML — reducing variance and improving prediction robustness.
- **Structured Deliberation** — Agents interact, challenge each other's reasoning, and converge on consensus through structured debate rounds. The final output is not a single opinion but a **calibrated collective forecast**.
- **Consensus Confidence Scoring** — The degree of agent agreement provides a built-in confidence metric. High consensus = high-conviction trade signal. Divergence = uncertainty flag.

### 📈 Predictive Event Analysis Roadmap

| Capability | Status | Description |
|---|---|---|
| Knowledge graph from unstructured data | ✅ Live | Ingest documents, news, transcripts → structured graph |
| Multi-agent persona generation | ✅ Live | Graph-aware agents with domain expertise |
| Parallel agent simulation & debate | ✅ Live | Independent reasoning + structured consensus |
| Final consensus report with confidence | ✅ Live | Aggregated prediction with supporting evidence |
| Prediction market API integration | 🔜 Roadmap | Direct integration with Polymarket / Kalshi APIs |
| Real-time event stream ingestion | 🔜 Roadmap | Live news feeds → continuous graph updates → agent re-evaluation |
| Backtesting framework | 🔜 Roadmap | Historical event replay to validate agent accuracy |
| Portfolio-level signal aggregation | 🔜 Roadmap | Multi-event, multi-market position management |
| On-chain agent wallets | 🔜 Roadmap | Autonomous agents with signing capability for DeFi prediction markets |

### 🏭 Why This Architecture Wins

1. **Self-hosted & private** — Your trading signals, data sources, and agent strategies never leave your infrastructure. Zero data leakage to third-party APIs (beyond LLM calls).
2. **Knowledge graph advantage** — Neo4j provides structured relational reasoning that flat-context LLMs cannot. Agents reason over entity relationships, causal chains, and temporal dependencies.
3. **Scalable consensus** — Spin up 5 agents or 50. More agents = richer deliberation = more robust predictions. The architecture scales horizontally.
4. **Auditable reasoning** — Every agent's reasoning chain is logged and queryable. Full transparency into *why* the system made a particular prediction — critical for regulatory compliance and strategy iteration.
5. **Model-agnostic** — Swap GPT-4o for Claude, Llama, Mistral, or any OpenAI-compatible endpoint. Mix models across agents for cognitive diversity.

> **TL;DR** — MiroFish Neo4j Fork transforms multi-agent AI simulation into an actionable prediction engine. Feed it information, let agents deliberate in parallel, extract consensus forecasts, and use those signals to trade prediction markets with conviction.

---

## Acknowledgments

Fork of [**MiroFish**](https://github.com/666ghj/MiroFish) by the MiroFish team. Simulation engine powered by [OASIS](https://github.com/camel-ai/oasis) from CAMEL-AI.

**Infrastructure:** [Neo4j](https://neo4j.com/) · [ChromaDB](https://www.trychroma.com/) · [OpenAI Whisper](https://openai.com/research/whisper) · [OpenAI GPT](https://openai.com/)

---

## License

Based on [MiroFish](https://github.com/666ghj/MiroFish) — licensed under [AGPL-3.0](https://github.com/666ghj/MiroFish/blob/main/LICENSE).

---

<div align="center">

*Built by [@0xrphl](https://github.com/0xrphl)*

</div>
