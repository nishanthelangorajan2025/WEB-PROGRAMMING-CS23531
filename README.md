# WEB PROGRAMMING Project CS23531
MEDIXAI · Explainable Expert System

A transparent, rule-based clinical decision support simulator built with React 18, Python 3, and SQLite.

📖 About the Project

MEDIXAI is an educational, full-stack expert system designed to demystify symbolic artificial intelligence. Unlike black-box neural networks, MEDIXAI exposes the exact reasoning pathways connecting reported clinical facts (symptoms) to diagnostic rules (disease hypotheses).

The system integrates:

Forward Rule Evaluation: Matches collected facts against weighted premises across 60+ disease rules.

Backward Premise Verification: Identifies unconfirmed required premises for top candidates and questions the user to confirm or refute them.

Contradiction Guards: Blocks contradictory inputs before evaluation fires.

Interactive Knowledge Base Expansion: Allows real-time addition of symptoms, diseases, weights, and rules with immediate SQLite persistence.

🌟 Key Features

1. Transparent Reasoning & Heuristic Scoring

Calculates heuristic match confidence using weighted fact overlap:

$$\text{Score} = \left(\frac{100 \times \sum w_{\text{matched}}}{\sum w_{\text{total}}}\right) \times (\text{if missing required premises}: 0.60 \text{ else } 1.00)$$

Generates human-readable formal logic traces (IF ... THEN ...) for every matched candidate.

2. Interactive Hypothesis Testing

For top candidate conditions, unanswered required premises appear with Yes, No, and Unsure actions. Answering dynamically recomputes candidate rankings in real time.

Optional unmatched symptoms can be toggled on-the-fly to evaluate score sensitivity.

3. Clinical Safety Guardrails

Contradiction Blocker: Evaluates mutually exclusive pairs (e.g., fever vs. no_fever, bradycardia vs. tachycardia) and prevents evaluation until corrected.

Red-Flag Triage Flags: Triggers high-visibility emergency warnings when life-threatening symptoms (e.g., crushing_chest_pain, stridor_laryngeal_edema, altered_mental_state) are asserted.

4. Dynamic Knowledge Base CRUD

Add new disease rules with custom severity, required premises, treatment notes, and precautions.

Register new symptoms and configure warning flags.

All modifications persist to SQLite via the REST backend, with automatic fallback to localStorage in standalone environments.

5. Audit & Evaluation History

Tracks each inference session with timestamps, present/absent fact sets, top candidate scores, and matched counts.

One-click restore loads historical fact sets back into the active workspace.

🏗 System Architecture

┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│  React 18 + Vite (SPA)                                      │
│  ├── Symptom Workspace (Forward / Backward Chaining UI)     │
│  ├── Knowledge Base Browser & CRUD Expansion Drawer         │
│  └── Evaluation History Logs (State Restoration)            │
└──────────────────────────────┬──────────────────────────────┘
                               │
            HTTP REST / JSON   │ Proxy: /api/* -> :8000
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend Layer                          │
│  Python 3 (http.server standard library)                    │
│  ├── GET  /api/state         Fetch KB, metadata & logs      │
│  ├── POST /api/diseases      Insert/update disease rule     │
│  ├── POST /api/symptoms      Register clinical symptom fact │
│  ├── POST /api/contradictions Register conflicting pair     │
│  └── POST /api/logs          Record evaluation trace        │
└──────────────────────────────┬──────────────────────────────┘
                               │
            SQL Queries        │ Executes DDL & Transactions
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Persistence Layer                       │
│  SQLite 3 (medixai.db)                                      │
│  ├── diseases            ├── symptoms                       │
│  ├── disease_symptoms    ├── contradictions                 │
│  └── evaluation_logs                                        │
└─────────────────────────────────────────────────────────────┘



🚀 Quick Start

Prerequisites

Make sure you have the following installed:

Node.js (v18.0 or newer)

Python (v3.8 or newer)

Installation & Setup

Clone the repository:

git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>



Start the Python + SQLite backend:
Open a terminal and run:

python app.py



The server will start at http://localhost:8000. On first run, it will automatically create and seed medixai.db with the clinical knowledge base.

Start the React frontend:
Open a second terminal and run:

npm install
npm run dev



Vite will start the frontend at http://localhost:5173. Open this URL in your browser. Vite is pre-configured to forward all /api/* requests to the Python server.

Alternative: Standalone Single-Server Run (No Node.js Required)

If you are demonstrating on a lab computer without Node.js installed:

python app.py



Open http://localhost:8000 directly. The Python server will serve the zero-dependency React 18 application connected to the SQLite database.

📁 Repository Structure

├── src/
│   ├── App.jsx            # Core React component (Workspace, KB CRUD, Logs, Method)
│   ├── App.css            # Responsive dark-theme styling
│   ├── initialData.js     # Default clinical dataset, contradiction rules & safety facts
│   └── main.jsx           # React DOM application mount point
├── app.py                 # Lightweight Python REST server & SQLite auto-seeder
├── index.html             # Vite entry HTML
├── package.json           # Frontend dependencies, build targets, and scripts
├── vite.config.js         # Vite configuration with backend proxy mapping
├── .gitignore             # Standard git exclusions (node_modules, build artifacts, db)
└── README.md              # Project documentation



🔌 API Reference

| Method | Endpoint | Description |
| GET | /api/state | Retrieves the complete knowledge base, symptoms metadata, contradiction rules, and evaluation logs. |
| POST | /api/diseases | Creates or updates a disease rule with its symptom weights and required premises. |
| POST | /api/symptoms | Registers a new symptom identifier, clinical note, and warning status. |
| POST | /api/contradictions | Registers a new pair of mutually exclusive symptoms. |
| POST | /api/logs | Appends a completed rule evaluation session to the history log. |
| DELETE | /api/logs | Clears all recorded evaluation history entries. |
