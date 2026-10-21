<div align="center">

# MEDIXAI · Explainable Expert System

**A transparent, rule-based clinical decision support simulator built with React 18, Python 3, and SQLite.**

[![React](https://img.shields.io/badge/React-18.x-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<p align="center">
  <a href="#-about-the-project">About</a> •
  <a href="#-key-features">Key Features</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-repository-structure">Structure</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-disclaimer">Disclaimer</a>
</p>

</div>

---

## 📖 About the Project

**MEDIXAI** is an educational, full-stack expert system designed to demystify symbolic artificial intelligence. Unlike black-box neural networks, MEDIXAI exposes the exact reasoning pathways connecting reported clinical facts (symptoms) to diagnostic rules (disease hypotheses).

The system integrates:
- **Forward Rule Evaluation**: Matches collected facts against weighted premises across 60+ disease rules.
- **Backward Premise Verification**: Identifies unconfirmed required premises for top candidates and questions the user to confirm or refute them.
- **Contradiction Guards**: Blocks contradictory inputs before evaluation fires.
- **Interactive Knowledge Base Expansion**: Allows real-time addition of symptoms, diseases, weights, and rules with immediate SQLite persistence.

---

## 🌟 Key Features

### 1. Transparent Reasoning & Heuristic Scoring
- Calculates heuristic match confidence using weighted fact overlap:
  $$\text{Score} = \left(\frac{100 \times \sum w_{\text{matched}}}{\sum w_{\text{total}}}\right) \times (\text{if missing required premises}: 0.60 \text{ else } 1.00)$$
- Generates human-readable formal logic traces (`IF ... THEN ...`) for every matched candidate.

### 2. Interactive Hypothesis Testing
- For top candidate conditions, unanswered required premises appear with `Yes`, `No`, and `Unsure` actions. Answering dynamically recomputes candidate rankings in real time.
- Optional unmatched symptoms can be toggled on-the-fly to evaluate score sensitivity.

### 3. Clinical Safety Guardrails
- **Contradiction Blocker**: Evaluates mutually exclusive pairs (e.g., `fever` vs. `no_fever`, `bradycardia` vs. `tachycardia`) and prevents evaluation until corrected.
- **Red-Flag Triage Flags**: Triggers high-visibility emergency warnings when life-threatening symptoms (e.g., `crushing_chest_pain`, `stridor_laryngeal_edema`, `altered_mental_state`) are asserted.

### 4. Dynamic Knowledge Base CRUD
- Add new disease rules with custom severity, required premises, treatment notes, and precautions.
- Register new symptoms and configure warning flags.
- All modifications persist to SQLite via the REST backend, with automatic fallback to `localStorage` in standalone environments.

### 5. Audit & Evaluation History
- Tracks each inference session with timestamps, present/absent fact sets, top candidate scores, and matched counts.
- One-click restore loads historical fact sets back into the active workspace.

---

## 🏗 System Architecture

```text
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
```

---

## 🚀 Quick Start

### Prerequisites
Make sure you have the following installed:
- [Node.js](https://nodejs.org/) (v18.0 or newer)
- [Python](https://www.python.org/) (v3.8 or newer)

---

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>
   ```

2. **Start the Python + SQLite backend:**
   Open a terminal and run:
   ```bash
   python app.py
   ```
   > The server will start at `http://localhost:8000`. On first run, it will automatically create and seed `medixai.db` with the clinical knowledge base.

3. **Start the React frontend:**
   Open a second terminal and run:
   ```bash
   npm install
   npm run dev
   ```
   > Vite will start the frontend at `http://localhost:5173`. Open this URL in your browser. Vite is pre-configured to forward all `/api/*` requests to the Python server.

---

### Alternative: Standalone Single-Server Run (No Node.js Required)

If you are demonstrating on a lab computer without Node.js installed:
```bash
python app.py
```
Open **`http://localhost:8000`** directly. The Python server will serve the zero-dependency React 18 application connected to the SQLite database.

---

## 📁 Repository Structure

```text
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
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/state` | Retrieves the complete knowledge base, symptoms metadata, contradiction rules, and evaluation logs. |
| `POST` | `/api/diseases` | Creates or updates a disease rule with its symptom weights and required premises. |
| `POST` | `/api/symptoms` | Registers a new symptom identifier, clinical note, and warning status. |
| `POST` | `/api/contradictions` | Registers a new pair of mutually exclusive symptoms. |
| `POST` | `/api/logs` | Appends a completed rule evaluation session to the history log. |
| `DELETE` | `/api/logs` | Clears all recorded evaluation history entries. |

---

## 🛡️ Disclaimer

> [!WARNING]
> **FOR EDUCATIONAL AND SIMULATION PURPOSES ONLY.**
> This project is designed strictly as an academic exploration of knowledge-based systems and forward/backward rule evaluation algorithms. It is **not** a diagnostic device, does **not** provide verified medical advice, and should never be used to make clinical or healthcare decisions. In the event of a medical emergency, immediately seek professional clinical help or contact local emergency services.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
