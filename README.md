# WEB-PROGRAMMING-CS23531
Here is an updated, professional, and well-structured **`README.md`** tailored specifically for your GitHub repository:

```markdown
# MEDIXAI · Explainable Expert System

[![React](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Python](https://img.shields.io/badge/Backend-Python%203%20(Standard%20Lib)-3776AB?logo=python&logoColor=white)](https://python.org/)
[![Database](https://img.shields.io/badge/Database-SQLite3-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Course](https://img.shields.io/badge/Coursework-CS23531%20Web%20Dev%20%7C%20CS23533%20FOAI-4B0082)](#)

> **Academic Project:** An interactive, explainable rule-based clinical expert system featuring forward rule evaluation, backward premise verification, contradiction detection, and dynamic SQLite persistence with a modern React 18 interface.

---

## 📌 Overview

**MEDIXAI** demonstrates how symbolic artificial intelligence and expert systems operate transparently without opaque black-box models. 

Given clinical observations (symptom facts), MEDIXAI executes a forward-evaluation inference pass across a relational knowledge base of diseases, symptoms, and weights. It ranks potential candidate conditions, highlights missing required premises, alerts users to red-flag triage emergencies, and allows users to dynamically expand the knowledge base through an integrated CRUD interface.

---

## ✨ Features

- **Transparent Rule Evaluation & Scoring:**
  - Evaluates rules via weighted symptom overlap:
    $$\text{score} = \left(\frac{100 \times \sum w_{\text{matched}}}{\sum w_{\text{total}}}\right) \times (\text{if missing required premises}: 0.60 \text{ else } 1.00)$$
  - Displays formal deduction derivations (`IF ... THEN ... [fired/not fired]`) for total explainability.

- **Backward Premise Verification & What-If Interactivity:**
  - Suggests unanswered required premises for top hypothesis candidates.
  - Interactive `Yes` / `No` / `Unsure` answering directly recomputes candidate rankings in real time.
  - Unmatched optional symptoms can be added dynamically from the details drawer.

- **Safety Triage & Contradiction Guardrails:**
  - Detects mutually exclusive symptom inputs (e.g., `fever` vs. `no_fever`, `diarrhea` vs. `constipation`) and halts evaluation until resolved.
  - Flags critical red-flag symptoms (e.g., `crushing_chest_pain`, `stridor_laryngeal_edema`, `altered_mental_state`) with emergency warning banners.

- **Dynamic Knowledge Base Expansion (CRUD):**
  - Add or update disease rules with custom weights, required subsets, severity levels, and clinical guidance.
  - Register new symptom facts and configure whether they trigger safety triage flags.
  - Add custom contradiction pairs.
  - Automatically persists updates to the SQLite relational database.

- **Evaluation History & State Restoration:**
  - Logs past evaluations with timestamps, fact sets, top candidate matches, and scores.
  - One-click restore button reloads any historical evaluation back into the active workspace.

- **Zero-Dependency Python Backend:**
  - The backend uses Python’s built-in standard library (`http.server`, `sqlite3`, `json`) — no `pip install` required.

---

## 🛠 Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | React 18, Vite | Declarative components, reactive state management, dark-mode CSS |
| **Backend** | Python 3 (`http.server`) | REST API handling state, CRUD updates, and logs |
| **Database** | SQLite 3 (`medixai.db`) | Relational tables (`diseases`, `symptoms`, `disease_symptoms`, `contradictions`, `evaluation_logs`) |
| **Architecture** | Client-Server Architecture | Vite proxy (`/api` → `http://localhost:8000`) with automatic offline `localStorage` fallback |

---

## 📁 Repository Structure

```text
.
├── src/
│   ├── App.jsx            # Main React application component (Workspace, KB, Logs, Method)
│   ├── App.css            # Dark-theme responsive stylesheet
│   ├── initialData.js     # Default clinical knowledge base, contradiction pairs & warnings
│   └── main.jsx           # React DOM root entry point
├── app.py                 # Python REST API server & auto-seeding SQLite backend
├── index.html             # Vite entry HTML
├── package.json           # Frontend dependencies and npm scripts
├── vite.config.js         # Vite configuration with /api reverse proxy
├── .gitignore             # Git ignore file for node_modules, build, and DB
└── README.md              # Project documentation

```

---

## 🚀 Quick Start Guide

### Prerequisites

* **Python 3.8+** installed (`python --version`)
* **Node.js 18+** & **npm** installed (`node --version`)

---

### Step 1: Clone the Repository

```bash
git clone [https://github.com/](https://github.com/)<your-username>/<your-repo-name>.git
cd <your-repo-name>

```

---

### Step 2: Start the Python SQLite Backend

In your first terminal:

```bash
python app.py

```

* **Output:** `MEDIXAI Full-Stack Server running at http://localhost:8000`
* *Note:* On the very first run, `app.py` automatically initializes and seeds `medixai.db` with the entire clinical knowledge base.

---

### Step 3: Start the React Development Server

In a second terminal:

```bash
npm install
npm run dev

```

* **Output:** Vite dev server running at `http://localhost:5173`
* Open **[http://localhost:5173](http://localhost:5173)** in your browser.

> Vite is pre-configured to forward all `/api/*` calls directly to the Python backend on port `8000`.

---

## 📦 Production Build (Optional)

If you wish to bundle the React frontend into static assets and serve everything from a single Python server:

1. Build the production bundle:
```bash
npm run build

```


2. Start the Python server:
```bash
python app.py

```


3. Open **`http://localhost:8000`** in your browser. The backend will automatically detect the `dist/` directory and serve the compiled React app directly.

---

## 📡 REST API Reference

The Python backend exposes the following endpoints:

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/state` | Returns the entire current state (all disease rules, symptoms metadata, contradictions, and logs). |
| `POST` | `/api/diseases` | Inserts or updates a disease rule with its associated symptoms and required premises. |
| `POST` | `/api/symptoms` | Registers a new symptom fact or updates an existing clinical definition/flag. |
| `POST` | `/api/contradictions` | Registers a new mutually exclusive symptom pair. |
| `POST` | `/api/logs` | Appends a completed rule evaluation session to the history log. |
| `DELETE` | `/api/logs` | Clears all evaluation history entries. |
