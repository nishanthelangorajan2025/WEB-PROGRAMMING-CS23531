# WEB-PROGRAMMING-CS23531

**MEDIXAI — Explainable Rule-Based Clinical Decision Support System**

A zero-dependency full-stack web application demonstrating glass-box symbolic AI, reactive DOM architecture, and hybrid SQLite and LocalStorage persistence.

**Overview**

**MEDIXAI** is an explainable clinical expert system built to make diagnostic rule evaluation completely transparent and inspectable. Unlike opaque machine-learning symptom checkers that output unverified probabilities, MEDIXAI models clinical knowledge explicitly as weighted symptom premises and required diagnostic conditions. Every evaluation exposes the exact matched weights, missing required premises, contradiction locks, and step-by-step logical derivation behind each candidate hypothesis.

From a software engineering perspective, MEDIXAI is architected as a self-contained, zero-framework full-stack web application. It pairs a custom Python HTTP and REST application server and a normalized five-table SQLite relational database with a reactive vanilla JavaScript (ES6+) single-page interface, semantic HTML5 progressive disclosure, and automatic client-side `localStorage` failover.

**Key Capabilities & System Metrics**

| System Dimension | Production Specification | Engineering Implementation |
| --- | --- | --- |
| **Clinical Knowledge Base** | 98 Disease Rules · 12 Specialties | Covers Respiratory, Cardiovascular, Digestive, Neurological, Viral, Bacterial, Skin, Endocrine, Urinary, Musculoskeletal, Hematological, and Emergency conditions. |
| **Symptom Vocabulary** | 397 Canonical Observation Facts | Normalized `snake_case` identifiers with clinical definitions, rule analytics, and red-flag triage indicators. |
| **Weighted Rule Graph** | 639 Premise Links · 236 Required | Bipartite disease-symptom mapping with integer weights (`1–10`) and mandatory premise constraints. |
| **Clinical Safety Engine** | 7 Contradiction Pairs · 19 Red Flags | Pre-inference conflict blocking (e.g., `fever` vs. `no_fever`) and immediate emergency banners for critical symptoms. |
| **Triage Stratification** | 4 Severity Tiers · 34 Urgent Rules | Classifies rules into Low (14), Moderate (43), Serious (26), and Emergency (15) severity with explicit escalation notices. |
| **Hybrid Persistence** | SQLite 3 + Browser LocalStorage | Full relational persistence when connected to the Python API, with seamless offline fallback to a 38-rule client store. |

**How the Inference Engine Works**

MEDIXAI evaluates symptom inputs through a four-stage deterministic reasoning pipeline:

**1. Tri-State Fact Representation**

The system distinguishes between three explicit observation states rather than treating unselected symptoms as negative evidence:

* **Present (`facts` Set)**: Symptoms actively reported by the user.
* **Explicitly Absent (`absent` Set)**: Required premises confirmed as absent during backward verification.
* **Unknown**: Unselected symptoms that have not yet been established or ruled out.

**2. Pre-Inference Consistency & Safety Gate**

Before scoring any disease rule, the engine checks the active fact set against mutually exclusive contradiction pairs:

* `fever` ↔ `no_fever`
* `high_fever` ↔ `no_fever`
* `diarrhea` ↔ `constipation`
* `weight_loss` ↔ `weight_gain`
* `unexplained_weight_loss` ↔ `weight_gain`
* `bradycardia` ↔ `tachycardia`
* `hypotension` ↔ `hypertension`

If conflicting observations coexist, forward evaluation halts and prompts the user to resolve the contradiction. Concurrently, selecting any of the 19 red-flag symptoms (such as `crushing_chest_pain`, `facial_droop`, `stridor_laryngeal_edema`, or `sudden_shortness_of_breath`) triggers an urgent clinical triage alert.

**3. Forward Weighted Overlap Scoring**

A single forward pass evaluates all 98 disease rules. For each disease $d$ with total symptom weight $W_{\text{total}}$ and matched symptom weight $W_{\text{matched}}$:

```text
BaseScore(d) = 100 * (W_matched / W_total)

If all required premises hold:
    FinalScore(d) = BaseScore(d)
If one or more required premises are missing:
    FinalScore(d) = 0.60 * BaseScore(d)

```

Candidates with at least one matched symptom are ranked in descending order of `FinalScore(d)`, with alphabetical tie-breaking.

**4. Interactive Backward Premise Chaining**

Selecting any candidate rule reveals its **Backward Premise Check** panel. For every missing required premise, the user can answer **Yes**, **No**, or **Unsure** in real time:

* **Yes**: Moves the premise into the `facts` Set, removes the `0.60` penalty once all required premises are met, and re-ranks all candidates.
* **No**: Moves the premise into the `absent` Set and marks the rule as logically blocked.
* **Unsure**: Retains the premise as unknown and preserves the current partial score.

**Web Programming Concepts Covered**

MEDIXAI serves as a comprehensive implementation of modern full-stack web engineering principles built entirely with native browser and Python standard-library APIs:

**1. HTTP Server & RESTful Application Routing**

* **Unified Web & Application Server**: `MedixAIRequestHandler` serves static frontend assets over `GET /` while exposing a JSON REST API across `/api/*` endpoints on port `8000`.
* **Request Stream & CORS Handling**: Reads raw request bodies via `Content-Length`, validates JSON payloads with structured `400 Bad Request` error responses, and supports cross-origin preflight requests via `do_OPTIONS` (`Access-Control-Allow-Origin: *`).
* **Single-Trip State Synchronization**: Every mutating `POST` or `DELETE` request returns the complete `fetch_full_state()` snapshot, eliminating redundant follow-up `GET` requests.

**2. Semantic HTML5 & Progressive Disclosure**

* **Structural Landmarks**: Uses `<header>`, `<nav role="tablist">`, `<main>`, `<section role="tabpanel">`, `<article class="card">`, `<aside class="notice">`, and `<footer>` for semantic document hierarchy.
* **Native Disclosure Widgets**: Uses `<details>` and `<summary>` tags to build collapsible clinical guidance panels, formal logic traces, evaluation log accordions, and the knowledge base CRUD drawer without external JavaScript plugins.
* **WAI-ARIA Accessibility**: Implements `role="tab"`, `aria-selected`, `aria-controls`, `aria-expanded`, and `aria-live="polite"` regions so assistive technologies announce dynamic rule evaluations seamlessly.

**3. Modern CSS3 Architecture, Box Model & Responsive Layouts**

* **Custom Properties (Design Tokens)**: Centralizes dark-mode color tokens (`--bg`, `--card`, `--ink`, `--muted`, `--line`, `--accent`, `--tint`, `--green`, `--red`, `--orange`) in `:root`.
* **Box Model & Relational Pseudo-Classes**: Applies universal `box-sizing: border-box`, `44px` minimum interactive hit targets, `3px solid` focus outlines via `:focus-visible`, and parent state highlighting via `.symptom-item:has(input:checked)`.
* **CSS Grid & Flexbox**: Combines a two-column split workspace (`.grid`), a three-column knowledge base card layout (`.kb-grid`), and Flexbox toolbars that adapt to mobile viewports via `@media (max-width: 760px)`.

**4. Client-Side JavaScript (ES6+), DOM Manipulation & Form Controls**

* **Interactive Form Controls**: Implements real-time substring search (`<input type="search">`), category filtering (`<select>`), autocomplete suggestions (`<datalist>`), symptom checkboxes (`<input type="checkbox">`), and multi-input CRUD forms (`<form>`, `<textarea>`).
* **Event Delegation & Roving Keyboard Focus**: Uses delegated event listeners (`e.target.closest(...)`) for dynamically rendered chips, premise buttons, and symptom drawers, alongside keyboard navigation (`ArrowRight`, `ArrowLeft`, `Home`, `End`) across tabs.
* **Input Parsing & XSS Defense**: Parses comma-separated `symptom:weight` pairs, normalizes identifiers to `snake_case`, clamps weights to `[1, 10]`, and sanitizes all dynamic strings via `esc()` before `innerHTML` rendering.

**5. Unidirectional State Dataflow & Client-Side View Routing**

```text
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│   Lifecycle Mount    │     │  Central State Store │     │ Pure View Renderers  │
│     loadState()      │────▶│  KB, facts, absent,  │────▶│   renderSymptoms()  │
│  Fetch /api/state or │     │  contradictions,     │     │   renderResults()    │
│  hydrate LocalStorage│     │  evaluationLogs      │     │   renderKB(), Logs() │
└──────────────────────┘     └──────────▲───────────┘     └──────────┬───────────┘
                                        │                            │
                                        │   User Events & API Sync   │
                                        └────────────────────────────┘

```

* **Declarative State-to-DOM Rendering**: State mutations in `facts`, `absent`, or `KB` invoke deterministic render functions (`renderFacts()`, `renderSymptoms()`, `renderResults()`, `renderKB()`, `renderLogs()`) that keep the UI synchronized.
* **Client-Side Tab Routing**: `showTab(id)` switches workspace views instantaneously without full-page reloads.

**6. Relational Database Design & Referential Integrity**

| Table Name | Primary & Foreign Keys | Columns & Constraints |
| --- | --- | --- |
| `diseases` | `PRIMARY KEY (name)` | `category`, `severity`, `emergency` (0/1), `description`, `treatment`, `precaution` |
| `symptoms` | `PRIMARY KEY (id)` | `note` (clinical definition), `warning_flag` (0/1 red-flag trigger) |
| `disease_symptoms` | `PRIMARY KEY (disease_name, symptom_id)` · `FOREIGN KEY ... ON DELETE CASCADE` | `weight` (integer 1–10), `is_required` (0/1 mandatory premise flag) |
| `contradictions` | `PRIMARY KEY (symptom_a, symptom_b)` | Pairs of mutually exclusive symptom identifiers |
| `evaluation_logs` | `PRIMARY KEY (id AUTOINCREMENT)` | `timestamp`, `present_facts` (JSON), `absent_facts` (JSON), `top_disease`, `top_score`, `candidate_count` |

**REST API Specification**

| Method | Endpoint | Request Body (JSON) | Action & Response |
| --- | --- | --- | --- |
| `GET` | `/api/state` | *None* | Returns `200 OK` with `kb`, `symptoms_meta`, `warning_facts`, `contradictions`, and the latest 25 `logs`. |
| `POST` | `/api/diseases` | `{ name, category, severity, emergency, description, symptoms, required, treatment, precaution }` | Validates required fields, clamps weights to `[1, 10]`, auto-registers new symptoms, and returns `201 Created` with updated state. |
| `POST` | `/api/symptoms` | `{ id, note, warning }` | Normalizes `id` to `snake_case`, upserts into `symptoms`, and returns `201 Created`. |
| `POST` | `/api/contradictions` | `{ symptom_a, symptom_b }` | Verifies distinct non-empty symptom IDs, inserts into `contradictions`, and returns `201 Created`. |
| `POST` | `/api/logs` | `{ present_facts, absent_facts, top_disease, top_score, candidate_count }` | Timestamps and logs an evaluation run into `evaluation_logs`, returning `201 Created`. |
| `DELETE` | `/api/logs` | *None* | Clears all records from `evaluation_logs` and returns `200 OK` with refreshed state. |

**Repository Layout**

```text
medixai/
├── app.py              (Full-stack Python HTTP server, REST API router, and SQLite initializer)
├── index.html          (Complete single-page application: UI, styling, and inference engine)
├── medixai.db          (Embedded SQLite 3 database: 98 diseases, 397 symptoms, 639 links)
└── README.md           (Project documentation and system architecture)

```

**How to Run It**

**Prerequisites**

* **Python 3.8+** (uses only standard library modules: `http.server`, `sqlite3`, `json`, `urllib.parse`, `datetime`, and `os`)
* **Web Browser**: Any modern browser (Chrome, Firefox, Edge, or Safari)

**Option 1: Full-Stack Mode (Python Server + SQLite Persistence)**

1. Clone the repository and navigate into the project folder:

```bash
git clone https://github.com/nishanthelangorajan2025/WEB-PROGRAMMING-CS23531.git
cd medixai

```

2. Start the backend server:

```bash
python3 app.py

```

3. Open the application in your browser:

```text
http://localhost:8000

```

The header badge will display **SQLite DB Connected**, and all custom diseases, symptoms, contradiction pairs, and evaluation logs will persist directly to `medixai.db`.

**Option 2: Standalone Static Mode (Zero-Server / Browser LocalStorage)**

Open `index.html` directly in your browser or deploy it to any static host (such as GitHub Pages). When `/api/state` is unreachable, the application automatically switches to **Local Storage DB Mode** and persists all changes to `localStorage` (`medixai_state_v2`).


