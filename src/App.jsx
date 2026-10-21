import React, { useState, useEffect, useMemo } from "react";
import { DEFAULT_KB, INITIAL_CONTRADICTIONS, INITIAL_WARNINGS } from "./initialData";
import "./App.css";

const label = (s) =>
  String(s)
    .replaceAll("_", " ")
    .replace(/^./, (c) => c.toUpperCase());

export default function App() {
  const [kb, setKb] = useState(() => structuredClone(DEFAULT_KB));
  const [symptomsMeta, setSymptomsMeta] = useState({});
  const [contradictions, setContradictions] = useState(INITIAL_CONTRADICTIONS);
  const [warningFacts, setWarningFacts] = useState(INITIAL_WARNINGS);
  const [evaluationLogs, setEvaluationLogs] = useState([]);
  const [serverOnline, setServerOnline] = useState(false);
  const [dbStatus, setDbStatus] = useState("Connecting DB…");

  // Workspace state
  const [activeTab, setActiveTab] = useState("assess");
  const [facts, setFacts] = useState(() => new Set());
  const [absent, setAbsent] = useState(() => new Set());
  const [expandedSymptoms, setExpandedSymptoms] = useState(() => new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");

  // Evaluation state
  const [hasEvaluated, setHasEvaluated] = useState(false);
  const [conflictError, setConflictError] = useState("");
  const [rankedResults, setRankedResults] = useState([]);
  const [activeDisease, setActiveDisease] = useState("");

  // Knowledge base tab state
  const [kbSearch, setKbSearch] = useState("");
  const [allKbExpanded, setAllKbExpanded] = useState(false);
  const [crudMessage, setCrudMessage] = useState(null);

  // Forms state
  const [dName, setDName] = useState("");
  const [dCategory, setDCategory] = useState("");
  const [dSeverity, setDSeverity] = useState("Moderate");
  const [dDesc, setDDesc] = useState("");
  const [dSymptoms, setDSymptoms] = useState("");
  const [dRequired, setDRequired] = useState("");
  const [dTreatment, setDTreatment] = useState("");
  const [dPrecaution, setDPrecaution] = useState("");
  const [dEmergency, setDEmergency] = useState(false);

  const [sId, setSId] = useState("");
  const [sNote, setSNote] = useState("");
  const [sWarn, setSWarn] = useState(false);

  const [cA, setCA] = useState("");
  const [cB, setCB] = useState("");

  const saveLocalBackup = (nextKb, nextMeta, nextContra, nextWarn, nextLogs) => {
    try {
      localStorage.setItem(
        "medixai_state_v2",
        JSON.stringify({
          KB: nextKb,
          symptomsMeta: nextMeta,
          contradictions: nextContra,
          warningFacts: nextWarn,
          evaluationLogs: nextLogs,
        })
      );
    } catch (err) {}
  };

  useEffect(() => {
    async function loadState() {
      try {
        const res = await fetch("/api/state");
        if (!res.ok) throw new Error("Offline");
        const data = await res.json();
        setKb(data.kb || DEFAULT_KB);
        setSymptomsMeta(data.symptoms_meta || {});
        setContradictions(data.contradictions || INITIAL_CONTRADICTIONS);
        setWarningFacts(data.warning_facts || INITIAL_WARNINGS);
        setEvaluationLogs(data.logs || []);
        setServerOnline(true);
        setDbStatus("SQLite DB Connected");
      } catch (e) {
        setServerOnline(false);
        const saved = localStorage.getItem("medixai_state_v2");
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            if (parsed.KB) setKb(parsed.KB);
            if (parsed.symptomsMeta) setSymptomsMeta(parsed.symptomsMeta);
            if (parsed.contradictions) setContradictions(parsed.contradictions);
            if (parsed.warningFacts) setWarningFacts(parsed.warningFacts);
            if (parsed.evaluationLogs) setEvaluationLogs(parsed.evaluationLogs);
          } catch (err) {}
        }
        setDbStatus("Local Storage DB Mode");
      }
    }
    loadState();
  }, []);

  const allSymptoms = useMemo(() => {
    const fromKb = Object.values(kb).flatMap((d) => Object.keys(d.symptoms));
    const fromMeta = Object.keys(symptomsMeta);
    return [...new Set([...fromKb, ...fromMeta])].sort();
  }, [kb, symptomsMeta]);

  const allCategories = useMemo(() => {
    return [...new Set(Object.values(kb).map((d) => d.category))].sort();
  }, [kb]);

  const shownSymptoms = useMemo(() => {
    const q = searchQuery.toLowerCase();
    const allowed = new Set(
      selectedCategory
        ? Object.values(kb)
            .filter((d) => d.category === selectedCategory)
            .flatMap((d) => Object.keys(d.symptoms))
        : allSymptoms
    );
    return allSymptoms.filter(
      (s) => allowed.has(s) && label(s).toLowerCase().includes(q)
    );
  }, [allSymptoms, kb, searchQuery, selectedCategory]);

  const getSymptomAnalytics = (s) => {
    const linked = [];
    let reqCount = 0;
    let maxWeight = 0;
    let sumWeight = 0;
    const cats = new Set();

    for (const [dName, d] of Object.entries(kb)) {
      if (s in d.symptoms) {
        const w = d.symptoms[s];
        const isReq = d.required.includes(s);
        linked.push({ name: dName, weight: w, isReq, category: d.category });
        if (isReq) reqCount++;
        if (w > maxWeight) maxWeight = w;
        sumWeight += w;
        cats.add(d.category);
      }
    }
    const avgWeight = linked.length ? (sumWeight / linked.length).toFixed(1) : 0;
    const contra = contradictions
      .filter((p) => p.includes(s))
      .map((p) => p.find((x) => x !== s));
    const isWarn = warningFacts.includes(s);
    const note =
      symptomsMeta[s]?.note ||
      (isWarn
        ? "Urgent triage safety indicator."
        : "Reported clinical symptom fact.");
    return {
      linked,
      reqCount,
      maxWeight,
      avgWeight,
      cats: [...cats],
      contra,
      isWarn,
      note,
    };
  };

  const computeEvaluation = (currentFacts, currentAbsent) => {
    return Object.entries(kb)
      .map(([name, d]) => {
        const matched = Object.keys(d.symptoms).filter((s) =>
          currentFacts.has(s)
        );
        const missing = d.required.filter((s) => !currentFacts.has(s));
        const blocked = d.required.filter((s) => currentAbsent.has(s));
        const optionalUnmatched = Object.keys(d.symptoms).filter(
          (s) => !currentFacts.has(s) && !d.required.includes(s)
        );
        const total = Object.values(d.symptoms).reduce((a, b) => a + b, 0);
        const weight = matched.reduce((a, s) => a + d.symptoms[s], 0);
        return {
          name,
          ...d,
          matched,
          missing,
          blocked,
          optionalUnmatched,
          weight,
          total,
          score: ((100 * weight) / total) * (missing.length ? 0.6 : 1),
        };
      })
      .filter((d) => d.matched.length)
      .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));
  };

  const recordEvaluationLog = async (
    presentArr,
    absentArr,
    topDisease,
    topScore,
    candidateCount
  ) => {
    const entry = {
      id: Date.now(),
      timestamp: new Date().toLocaleString(),
      present_facts: presentArr,
      absent_facts: absentArr,
      top_disease: topDisease,
      top_score: Number(topScore.toFixed(1)),
      candidate_count: candidateCount,
    };
    if (serverOnline) {
      try {
        const res = await fetch("/api/logs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(entry),
        });
        if (res.ok) {
          const state = await res.json();
          setEvaluationLogs(state.logs || []);
          return;
        }
      } catch (e) {}
    }
    const nextLogs = [entry, ...evaluationLogs];
    setEvaluationLogs(nextLogs);
    saveLocalBackup(kb, symptomsMeta, contradictions, warningFacts, nextLogs);
  };

  const runEvaluation = (
    customFacts = facts,
    customAbsent = absent,
    skipLog = false,
    preferredActive = activeDisease
  ) => {
    setHasEvaluated(true);
    const pairs = contradictions.filter((p) =>
      p.every((s) => customFacts.has(s))
    );
    if (pairs.length) {
      setRankedResults([]);
      setActiveDisease("");
      setConflictError(
        "Conflicting input: " +
          pairs.map((p) => p.map(label).join(" + ")).join("; ") +
          ". Remove or correct one fact in each pair before continuing."
      );
      return;
    }
    setConflictError("");
    const results = computeEvaluation(customFacts, customAbsent);
    setRankedResults(results);
    if (!results.length) {
      setActiveDisease("");
      return;
    }
    const nextActive = results.some((d) => d.name === preferredActive)
      ? preferredActive
      : results[0].name;
    setActiveDisease(nextActive);
    if (!skipLog) {
      recordEvaluationLog(
        [...customFacts],
        [...customAbsent],
        results[0].name,
        results[0].score,
        results.length
      );
    }
  };

  const toggleSymptomFact = (s) => {
    const nextFacts = new Set(facts);
    const nextAbsent = new Set(absent);
    if (nextFacts.has(s)) {
      nextFacts.delete(s);
    } else {
      nextFacts.add(s);
      nextAbsent.delete(s);
    }
    setFacts(nextFacts);
    setAbsent(nextAbsent);
    setHasEvaluated(false);
    setRankedResults([]);
    setConflictError("");
  };

  const handlePremiseAnswer = (symptom, value) => {
    const nextFacts = new Set(facts);
    const nextAbsent = new Set(absent);
    if (value === "yes") {
      nextFacts.add(symptom);
      nextAbsent.delete(symptom);
    } else {
      nextFacts.delete(symptom);
      if (value === "no") nextAbsent.add(symptom);
      else nextAbsent.delete(symptom);
    }
    setFacts(nextFacts);
    setAbsent(nextAbsent);
    runEvaluation(nextFacts, nextAbsent, true, activeDisease);
  };

  const handleTryDemo = () => {
    const demoFacts = new Set([
      "high_fever",
      "body_pain",
      "fatigue",
      "dry_cough",
    ]);
    const emptyAbsent = new Set();
    setFacts(demoFacts);
    setAbsent(emptyAbsent);
    runEvaluation(demoFacts, emptyAbsent, false, "");
  };

  const handleClearFacts = () => {
    setFacts(new Set());
    setAbsent(new Set());
    setHasEvaluated(false);
    setRankedResults([]);
    setActiveDisease("");
    setConflictError("");
  };

  const handleToggleAllSymptoms = () => {
    if (expandedSymptoms.size > 0) {
      setExpandedSymptoms(new Set());
    } else {
      setExpandedSymptoms(new Set(allSymptoms));
    }
  };

  const handleJumpToKb = (diseaseName) => {
    setActiveTab("kb");
    setKbSearch(diseaseName);
    setAllKbExpanded(true);
  };

  const handleLoadDiseaseToWorkspace = (diseaseName) => {
    const d = kb[diseaseName];
    if (!d) return;
    const nextFacts = new Set(d.required);
    const nextAbsent = new Set();
    setFacts(nextFacts);
    setAbsent(nextAbsent);
    setActiveTab("assess");
    runEvaluation(nextFacts, nextAbsent, false, diseaseName);
  };

  const handleRestoreLog = (log) => {
    const nextFacts = new Set(log.present_facts || []);
    const nextAbsent = new Set(log.absent_facts || []);
    setFacts(nextFacts);
    setAbsent(nextAbsent);
    setActiveTab("assess");
    runEvaluation(nextFacts, nextAbsent, true, log.top_disease || "");
  };

  const handleClearLogs = async () => {
    setEvaluationLogs([]);
    if (serverOnline) {
      try {
        await fetch("/api/logs", { method: "DELETE" });
      } catch (e) {}
    }
    saveLocalBackup(kb, symptomsMeta, contradictions, warningFacts, []);
  };

  const handleAddDisease = async (e) => {
    e.preventDefault();
    const name = dName.trim();
    const category = dCategory.trim();
    const description = dDesc.trim();
    const treatment = dTreatment.trim();
    const precaution = dPrecaution.trim();

    const symptomsObj = {};
    for (const pair of dSymptoms.split(",")) {
      const [k, v] = pair.split(":");
      if (!k || !v) continue;
      const sKey = k.trim().toLowerCase().replace(/\s+/g, "_");
      const weight = Math.max(1, Math.min(10, parseInt(v.trim(), 10) || 5));
      if (sKey) symptomsObj[sKey] = weight;
    }
    const requiredArr = dRequired
      .split(",")
      .map((s) => s.trim().toLowerCase().replace(/\s+/g, "_"))
      .filter((s) => s && s in symptomsObj);

    if (!Object.keys(symptomsObj).length || !requiredArr.length) {
      setCrudMessage({
        text: "Validation error: Provide valid 'symptom:weight' pairs and ensure required premises exist in the symptom list.",
        isError: true,
      });
      return;
    }

    const payload = {
      name,
      category,
      severity: dSeverity,
      emergency: dEmergency,
      description,
      symptoms: symptomsObj,
      required: requiredArr,
      treatment,
      precaution,
    };

    if (serverOnline) {
      try {
        const res = await fetch("/api/diseases", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (res.ok) {
          const state = await res.json();
          setKb(state.kb);
          if (state.symptoms_meta) setSymptomsMeta(state.symptoms_meta);
          setDName("");
          setDCategory("");
          setDDesc("");
          setDSymptoms("");
          setDRequired("");
          setDTreatment("");
          setDPrecaution("");
          setDEmergency(false);
          setCrudMessage({
            text: `Disease rule "${name}" saved to SQLite database.`,
            isError: false,
          });
          return;
        }
      } catch (err) {}
    }

    const nextKb = {
      ...kb,
      [name]: {
        category,
        severity: dSeverity,
        emergency: dEmergency,
        description,
        symptoms: symptomsObj,
        required: requiredArr,
        treatment,
        precaution,
      },
    };
    setKb(nextKb);
    saveLocalBackup(
      nextKb,
      symptomsMeta,
      contradictions,
      warningFacts,
      evaluationLogs
    );
    setDName("");
    setDCategory("");
    setDDesc("");
    setDSymptoms("");
    setDRequired("");
    setDTreatment("");
    setDPrecaution("");
    setDEmergency(false);
    setCrudMessage({
      text: `Disease rule "${name}" added and persisted.`,
      isError: false,
    });
  };

  const handleAddSymptom = async (e) => {
    e.preventDefault();
    const id = sId.trim().toLowerCase().replace(/\s+/g, "_");
    const note = sNote.trim();
    if (!id) return;

    if (serverOnline) {
      try {
        const res = await fetch("/api/symptoms", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, note, warning: sWarn }),
        });
        if (res.ok) {
          const state = await res.json();
          setSymptomsMeta(state.symptoms_meta);
          setWarningFacts(state.warning_facts);
          setSId("");
          setSNote("");
          setSWarn(false);
          setCrudMessage({
            text: `Symptom fact "${label(id)}" saved to SQLite database.`,
            isError: false,
          });
          return;
        }
      } catch (err) {}
    }

    const nextMeta = { ...symptomsMeta, [id]: { note, warning: sWarn } };
    const nextWarn =
      sWarn && !warningFacts.includes(id)
        ? [...warningFacts, id]
        : warningFacts;
    setSymptomsMeta(nextMeta);
    setWarningFacts(nextWarn);
    saveLocalBackup(kb, nextMeta, contradictions, nextWarn, evaluationLogs);
    setSId("");
    setSNote("");
    setSWarn(false);
    setCrudMessage({
      text: `Symptom fact "${label(id)}" registered.`,
      isError: false,
    });
  };

  const handleAddContradiction = async (e) => {
    e.preventDefault();
    const a = cA.trim().toLowerCase().replace(/\s+/g, "_");
    const b = cB.trim().toLowerCase().replace(/\s+/g, "_");
    if (!a || !b || a === b) {
      setCrudMessage({
        text: "Please enter two distinct symptom names.",
        isError: true,
      });
      return;
    }

    if (serverOnline) {
      try {
        const res = await fetch("/api/contradictions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symptom_a: a, symptom_b: b }),
        });
        if (res.ok) {
          const state = await res.json();
          setContradictions(state.contradictions);
          setCA("");
          setCB("");
          setCrudMessage({
            text: `Contradiction pair "${label(a)} ↔ ${label(b)}" saved.`,
            isError: false,
          });
          return;
        }
      } catch (err) {}
    }

    const nextContra = [...contradictions, [a, b]];
    setContradictions(nextContra);
    saveLocalBackup(kb, symptomsMeta, nextContra, warningFacts, evaluationLogs);
    setCA("");
    setCB("");
    setCrudMessage({
      text: `Contradiction pair "${label(a)} ↔ ${label(b)}" added.`,
      isError: false,
    });
  };

  const filteredKbEntries = useMemo(() => {
    const q = kbSearch.toLowerCase();
    return Object.entries(kb).filter(([n, d]) => {
      const text = (
        n +
        " " +
        d.category +
        " " +
        d.severity +
        " " +
        Object.keys(d.symptoms).map(label).join(" ")
      ).toLowerCase();
      return text.includes(q);
    });
  }, [kb, kbSearch]);

  const activeCandidate = useMemo(() => {
    return (
      rankedResults.find((r) => r.name === activeDisease) || rankedResults[0]
    );
  }, [rankedResults, activeDisease]);

  const activeWarnings = useMemo(() => {
    return warningFacts.filter((s) => facts.has(s));
  }, [warningFacts, facts]);

  return (
    <div className="shell">
      <header>
        <div className="brand">
          <span className="logo" aria-hidden="true">
            +
          </span>
          MEDIXAI
        </div>
        <div className="subtle">CS23531 Web Programming · CS23533 FOAI Lab</div>
        <span className="badge">{dbStatus}</span>
      </header>

      <section className="hero">
        <div>
          <span className="subtle">
            RULE-BASED · EXPANDABLE KNOWLEDGE BASE · REACT + SQLITE
          </span>
          <h1>Symptoms in. Reasoning out.</h1>
          <p className="muted">
            Explore how an expert system connects symptom facts to disease
            rules—and dynamically expand symptoms, clinical protocols, and
            rules.
          </p>
        </div>
        <div className="stats">
          {Object.keys(kb).length} disease rules
          <br />
          {allSymptoms.length} symptom facts · {allCategories.length} categories
        </div>
      </section>

      <div className="steps">
        <span>
          <b>1</b> Collect &amp; expand facts
        </span>
        <span>
          <b>2</b> Evaluate rules
        </span>
        <span>
          <b>3</b> Inspect &amp; expand knowledge base
        </span>
      </div>

      <nav className="nav" aria-label="Workspace tabs" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === "assess"}
          onClick={() => setActiveTab("assess")}
        >
          Symptom workspace
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "kb"}
          onClick={() => setActiveTab("kb")}
        >
          Knowledge base &amp; expand
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "logs"}
          onClick={() => setActiveTab("logs")}
        >
          Evaluation logs ({evaluationLogs.length})
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "method"}
          onClick={() => setActiveTab("method")}
        >
          How it works
        </button>
      </nav>

      <main>
        {activeTab === "assess" && (
          <section role="tabpanel">
            <div className="grid">
              <section className="card">
                <div className="row">
                  <div>
                    <h2>Build your fact set</h2>
                    <p className="subtle">
                      Select symptoms or click <strong>▾</strong> on any symptom
                      to expand its rule analytics.
                    </p>
                  </div>
                  <button type="button" onClick={handleTryDemo}>
                    Try example
                  </button>
                </div>

                <div className="toolbar">
                  <input
                    type="search"
                    aria-label="Search symptoms"
                    placeholder="Search symptoms…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <select
                    aria-label="Filter symptoms by disease category"
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                  >
                    <option value="">All categories</option>
                    {allCategories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="row" style={{ marginBottom: 8 }}>
                  <span className="subtle">
                    Showing {shownSymptoms.length} of {allSymptoms.length}{" "}
                    symptoms
                  </span>
                  <button
                    type="button"
                    onClick={handleToggleAllSymptoms}
                    style={{
                      minHeight: 32,
                      padding: "4px 10px",
                      fontSize: 13,
                    }}
                  >
                    {expandedSymptoms.size > 0
                      ? "Collapse details"
                      : "Expand visible details"}
                  </button>
                </div>

                <div className="symptoms">
                  {shownSymptoms.length === 0 ? (
                    <p className="muted">No symptoms match your search.</p>
                  ) : (
                    shownSymptoms.map((s) => {
                      const isExp = expandedSymptoms.has(s);
                      const isChecked = facts.has(s);
                      const info = isExp ? getSymptomAnalytics(s) : null;
                      return (
                        <div
                          key={s}
                          className={`symptom-item ${
                            isChecked ? "checked" : ""
                          }`}
                        >
                          <div className="symptom-head">
                            <label className="symptom">
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => toggleSymptomFact(s)}
                              />
                              <span>{label(s)}</span>
                            </label>
                            <button
                              type="button"
                              className="expand-btn"
                              aria-expanded={isExp}
                              title="Expand symptom details"
                              onClick={() => {
                                const next = new Set(expandedSymptoms);
                                if (next.has(s)) next.delete(s);
                                else next.add(s);
                                setExpandedSymptoms(next);
                              }}
                            >
                              {isExp ? "▴" : "▾"}
                            </button>
                          </div>
                          {isExp && info && (
                            <div className="symptom-drawer">
                              <p
                                className="subtle"
                                style={{ marginBottom: 6 }}
                              >
                                {info.note}
                              </p>
                              <div
                                className="tags"
                                style={{ margin: "4px 0 8px" }}
                              >
                                <span className="tag">
                                  Rules: {info.linked.length}
                                </span>
                                <span className="tag">
                                  Avg wt: {info.avgWeight} (Max {info.maxWeight}
                                  )
                                </span>
                                {info.reqCount > 0 && (
                                  <span className="tag good">
                                    Required in {info.reqCount}
                                  </span>
                                )}
                                {info.isWarn && (
                                  <span
                                    className="tag"
                                    style={{ color: "var(--red)" }}
                                  >
                                    Safety Red-Flag
                                  </span>
                                )}
                                {info.contra.length > 0 && (
                                  <span className="tag warn">
                                    Conflicts: {info.contra.map(label).join(", ")}
                                  </span>
                                )}
                              </div>
                              {info.linked.length > 0 ? (
                                <>
                                  <div className="subtle">
                                    Linked diseases (click to inspect in KB):
                                  </div>
                                  <div
                                    className="tags"
                                    style={{ margin: "4px 0 0" }}
                                  >
                                    {info.linked.map((l) => (
                                      <button
                                        key={l.name}
                                        type="button"
                                        className="tag-btn"
                                        onClick={() => handleJumpToKb(l.name)}
                                      >
                                        {l.name} ({l.weight}
                                        {l.isReq ? "*" : ""})
                                      </button>
                                    ))}
                                  </div>
                                </>
                              ) : (
                                <span className="subtle">
                                  No disease rules currently linked.
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>

                <div className="selection">
                  <div className="row">
                    <h3>
                      Selected facts <span className="muted">{facts.size}</span>
                    </h3>
                    <button type="button" onClick={handleClearFacts}>
                      Clear all
                    </button>
                  </div>
                  <div className="chips">
                    {facts.size === 0 ? (
                      <span className="subtle">No facts selected yet.</span>
                    ) : (
                      [...facts].map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => toggleSymptomFact(s)}
                          aria-label={`Remove ${label(s)}`}
                        >
                          {label(s)} ×
                        </button>
                      ))
                    )}
                  </div>
                  <div className="footer-actions">
                    <button
                      type="button"
                      className="primary"
                      disabled={facts.size === 0}
                      onClick={() => runEvaluation(facts, absent, false)}
                    >
                      Evaluate rules →
                    </button>
                  </div>
                  <div className="note">
                    Unselected symptoms are unknown—not absent. Evaluations and
                    custom expansions persist to the SQLite database (with
                    automatic browser storage backup).
                  </div>
                </div>
              </section>

              <section
                className="card"
                aria-label="Rule evaluation results"
                aria-live="polite"
              >
                {!hasEvaluated ? (
                  <>
                    <div className="row">
                      <h2>Reasoning workspace</h2>
                      <span className="badge">Ready</span>
                    </div>
                    <div className="empty">
                      <div className="icon" aria-hidden="true">
                        ⊢
                      </div>
                      <h3>
                        {facts.size > 0
                          ? "Facts updated."
                          : "A clear path from facts to rules."}
                      </h3>
                      <p className="muted">
                        Add symptoms, then evaluate the knowledge base to
                        inspect ranked matches, missing premises, and expandable
                        clinical guidance.
                      </p>
                    </div>
                    <div className="note">
                      A rule-match score is a heuristic overlap score. It is not
                      a probability or a medical diagnosis.
                    </div>
                  </>
                ) : conflictError ? (
                  <>
                    <h2>Review your facts</h2>
                    <div className="error">{conflictError}</div>
                  </>
                ) : rankedResults.length === 0 ? (
                  <>
                    <h2>No matching rules</h2>
                    <p className="muted">
                      The knowledge base has no overlap with these facts. This
                      does not rule out illness.
                    </p>
                  </>
                ) : (
                  <>
                    <div className="row">
                      <div>
                        <h2>Rule-match results</h2>
                        <span className="subtle">
                          {rankedResults.length} candidates · {facts.size}{" "}
                          present facts
                        </span>
                      </div>
                      <span className="badge">Evaluated</span>
                    </div>

                    {activeWarnings.length > 0 && (
                      <div className="error" style={{ marginTop: 12 }}>
                        Safety notice: {activeWarnings.map(label).join(", ")}{" "}
                        reported. This demo cannot assess urgency. Seek prompt
                        medical advice; severe symptoms require emergency care.
                      </div>
                    )}

                    <div className="result-list">
                      {rankedResults.map((r) => (
                        <button
                          key={r.name}
                          type="button"
                          className={`candidate ${
                            activeCandidate?.name === r.name ? "active" : ""
                          }`}
                          aria-pressed={activeCandidate?.name === r.name}
                          onClick={() => setActiveDisease(r.name)}
                        >
                          <span>
                            <strong>{r.name}</strong>
                            <span
                              className="badge"
                              style={{ marginLeft: 6, fontSize: 12 }}
                            >
                              {r.severity}
                            </span>
                            <br />
                            <span className="subtle">
                              {r.category} ·{" "}
                              {r.blocked.length
                                ? "Required fact absent"
                                : r.missing.length
                                ? "Incomplete premises"
                                : "Required premises met"}
                            </span>
                          </span>
                          <span className="score">
                            {r.score.toFixed(1)}
                            <span className="subtle">%</span>
                          </span>
                        </button>
                      ))}
                    </div>

                    <p className="subtle">
                      Scores measure weighted rule overlap—not clinical
                      confidence.
                    </p>

                    {activeCandidate && (
                      <div className="detail">
                        <div className="row">
                          <h3>{activeCandidate.name}</h3>
                          <div>
                            <span className="badge">
                              {activeCandidate.category}
                            </span>
                            <span
                              className="badge"
                              style={{ marginLeft: 4 }}
                            >
                              Severity: {activeCandidate.severity}
                            </span>
                          </div>
                        </div>
                        <p className="muted">{activeCandidate.description}</p>

                        <h3>
                          Matched evidence ({activeCandidate.matched.length} /{" "}
                          {Object.keys(activeCandidate.symptoms).length})
                        </h3>
                        <div className="tags">
                          {activeCandidate.matched.map((s) => (
                            <span key={s} className="tag good">
                              ✓ {label(s)} ({activeCandidate.symptoms[s]})
                            </span>
                          ))}
                        </div>

                        <h3>Backward premise check</h3>
                        <p className="subtle">
                          {activeCandidate.blocked.length
                            ? "Rule blocked by an explicitly absent required fact."
                            : activeCandidate.missing.length
                            ? "These required premises are not yet established."
                            : "All required premises hold in this academic rule. This is not a confirmed diagnosis."}
                        </p>
                        <div className="questions">
                          {activeCandidate.missing.map((s) => (
                            <div key={s} className="question">
                              <div className="row">
                                <span>
                                  {label(s)} (wt {activeCandidate.symptoms[s]})
                                  {absent.has(s) ? " · Absent" : " · Unknown"}
                                </span>
                                <span style={{ display: "flex", gap: 6 }}>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      handlePremiseAnswer(s, "yes")
                                    }
                                  >
                                    Yes
                                  </button>
                                  <button
                                    type="button"
                                    aria-pressed={absent.has(s)}
                                    onClick={() => handlePremiseAnswer(s, "no")}
                                  >
                                    No
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      handlePremiseAnswer(s, "unknown")
                                    }
                                  >
                                    Unsure
                                  </button>
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>

                        <details className="expand-panel" open>
                          <summary>
                            Expand clinical guidance, precautions &amp; severity
                            protocol
                          </summary>
                          <div className="expand-panel-body">
                            <p>
                              <strong>Supportive Treatment Guidance:</strong>{" "}
                              {activeCandidate.treatment}
                            </p>
                            <p>
                              <strong>Precautions &amp; Observation:</strong>{" "}
                              {activeCandidate.precaution}
                            </p>
                            <p className="subtle" style={{ margin: 0 }}>
                              Severity classification:{" "}
                              <strong>{activeCandidate.severity}</strong> ·
                              Emergency triage flag:{" "}
                              <strong>
                                {activeCandidate.emergency ? "Active" : "None"}
                              </strong>
                            </p>
                          </div>
                        </details>

                        <details className="expand-panel">
                          <summary>
                            Expand unmatched optional symptoms (
                            {activeCandidate.optionalUnmatched.length}{" "}
                            remaining)
                          </summary>
                          <div className="expand-panel-body">
                            <p className="subtle">
                              Click any optional symptom below to add it as
                              present and recompute the score:
                            </p>
                            <div className="tags">
                              {activeCandidate.optionalUnmatched.length > 0 ? (
                                activeCandidate.optionalUnmatched.map((s) => (
                                  <button
                                    key={s}
                                    type="button"
                                    className="tag-btn"
                                    onClick={() =>
                                      handlePremiseAnswer(s, "yes")
                                    }
                                  >
                                    + {label(s)} (wt{" "}
                                    {activeCandidate.symptoms[s]})
                                  </button>
                                ))
                              ) : (
                                <span className="subtle">
                                  All optional symptoms for this rule are
                                  already selected.
                                </span>
                              )}
                            </div>
                          </div>
                        </details>

                        <details className="expand-panel">
                          <summary>
                            Expand formal logical trace &amp; score derivation
                          </summary>
                          <div className="expand-panel-body">
                            <pre className="logic">
                              {`IF ${activeCandidate.required
                                .map(label)
                                .join(" AND ")}
THEN ${activeCandidate.name} [academic rule]

Rule: ${
                                activeCandidate.blocked.length
                                  ? "blocked (required fact absent)"
                                  : activeCandidate.missing.length
                                  ? "not fired (premises unknown)"
                                  : "fired (required facts present)"
                              }
Matched weight: ${activeCandidate.weight} / ${activeCandidate.total}
Missing-premise multiplier: ${
                                activeCandidate.missing.length ? "0.60" : "1.00"
                              }
Rule-match score: ${activeCandidate.score.toFixed(1)}%`}
                            </pre>
                          </div>
                        </details>

                        {activeCandidate.emergency && (
                          <div className="error" style={{ marginTop: 12 }}>
                            The source marks this rule as serious or urgent. A
                            rule flag is not validated clinical triage; consult
                            a medical professional.
                          </div>
                        )}
                        <div className="note">
                          This academic output cannot diagnose or recommend a
                          treatment. Consult a qualified clinician for
                          assessment and care.
                        </div>
                      </div>
                    )}
                  </>
                )}
              </section>
            </div>
          </section>
        )}

        {activeTab === "kb" && (
          <section role="tabpanel">
            <details className="card crud-box">
              <summary>
                + Expand Knowledge Base (Add New Symptom, Disease Rule, or
                Contradiction Pair)
              </summary>
              {crudMessage && (
                <div
                  className={crudMessage.isError ? "error" : "success"}
                  style={{ marginTop: 12 }}
                >
                  {crudMessage.text}
                </div>
              )}
              <div className="form-grid">
                <form
                  onSubmit={handleAddDisease}
                  className="card"
                  style={{ padding: 18, background: "var(--bg)" }}
                >
                  <h3>Add or Update Disease Rule</h3>
                  <p className="subtle">
                    Persists directly into the relational database and updates
                    symptom mappings.
                  </p>
                  <div className="form-group">
                    <label>Disease Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g., Seasonal Tonsillitis"
                      value={dName}
                      onChange={(e) => setDName(e.target.value)}
                    />
                  </div>
                  <div className="row" style={{ gap: 8 }}>
                    <div className="form-group" style={{ flex: 1 }}>
                      <label>Category *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g., Respiratory"
                        list="category-list"
                        value={dCategory}
                        onChange={(e) => setDCategory(e.target.value)}
                      />
                      <datalist id="category-list">
                        {allCategories.map((c) => (
                          <option key={c} value={c} />
                        ))}
                      </datalist>
                    </div>
                    <div className="form-group" style={{ flex: 1 }}>
                      <label>Severity *</label>
                      <select
                        style={{ maxWidth: "none" }}
                        value={dSeverity}
                        onChange={(e) => setDSeverity(e.target.value)}
                      >
                        <option value="Low">Low</option>
                        <option value="Moderate">Moderate</option>
                        <option value="Serious">Serious</option>
                        <option value="Emergency">Emergency</option>
                      </select>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Clinical Description *</label>
                    <input
                      type="text"
                      required
                      placeholder="Short summary of the condition…"
                      value={dDesc}
                      onChange={(e) => setDDesc(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>
                      Weighted Symptoms (format: symptom_name:weight, 1–10) *
                    </label>
                    <textarea
                      required
                      placeholder="sore_throat:10, fever:8, difficulty_swallowing:9, swollen_glands:7"
                      value={dSymptoms}
                      onChange={(e) => setDSymptoms(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>
                      Required Premises (comma-separated subset of symptoms) *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="sore_throat, fever"
                      value={dRequired}
                      onChange={(e) => setDRequired(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Supportive Treatment Guidance *</label>
                    <input
                      type="text"
                      required
                      placeholder="Warm fluids, rest, and clinical observation."
                      value={dTreatment}
                      onChange={(e) => setDTreatment(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Precaution &amp; Monitoring Note *</label>
                    <input
                      type="text"
                      required
                      placeholder="Monitor airway and hydration."
                      value={dPrecaution}
                      onChange={(e) => setDPrecaution(e.target.value)}
                    />
                  </div>
                  <label className="symptom" style={{ marginBottom: 12 }}>
                    <input
                      type="checkbox"
                      checked={dEmergency}
                      onChange={(e) => setDEmergency(e.target.checked)}
                    />{" "}
                    Mark as Urgent / Emergency Triage Rule
                  </label>
                  <button
                    type="submit"
                    className="primary"
                    style={{ width: "100%" }}
                  >
                    Save Disease Rule to Database
                  </button>
                </form>

                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 16,
                  }}
                >
                  <form
                    onSubmit={handleAddSymptom}
                    className="card"
                    style={{ padding: 18, background: "var(--bg)" }}
                  >
                    <h3>Add or Expand Symptom Fact</h3>
                    <p className="subtle">
                      Register a new standalone symptom or enrich an existing
                      symptom&apos;s clinical note.
                    </p>
                    <div className="form-group">
                      <label>Symptom Name *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g., joint_stiffness"
                        value={sId}
                        onChange={(e) => setSId(e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label>Clinical Definition / Expansion Note *</label>
                      <input
                        type="text"
                        required
                        placeholder="Reduced mobility or discomfort in joints."
                        value={sNote}
                        onChange={(e) => setSNote(e.target.value)}
                      />
                    </div>
                    <label className="symptom" style={{ marginBottom: 12 }}>
                      <input
                        type="checkbox"
                        checked={sWarn}
                        onChange={(e) => setSWarn(e.target.checked)}
                      />{" "}
                      Trigger Safety Warning Banner When Selected
                    </label>
                    <button
                      type="submit"
                      className="primary"
                      style={{ width: "100%" }}
                    >
                      Save Symptom Fact
                    </button>
                  </form>

                  <form
                    onSubmit={handleAddContradiction}
                    className="card"
                    style={{ padding: 18, background: "var(--bg)" }}
                  >
                    <h3>Add Contradiction Rule Pair</h3>
                    <p className="subtle">
                      Prevent conflicting symptom inputs during forward rule
                      evaluation.
                    </p>
                    <div className="row" style={{ gap: 8 }}>
                      <div className="form-group" style={{ flex: 1 }}>
                        <label>Symptom A *</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g., insomnia"
                          value={cA}
                          onChange={(e) => setCA(e.target.value)}
                        />
                      </div>
                      <div className="form-group" style={{ flex: 1 }}>
                        <label>Symptom B *</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g., hypersomnia"
                          value={cB}
                          onChange={(e) => setCB(e.target.value)}
                        />
                      </div>
                    </div>
                    <button type="submit" style={{ width: "100%" }}>
                      Add Contradiction Pair
                    </button>
                  </form>
                </div>
              </div>
            </details>

            <div className="row">
              <div>
                <h2>Inside the knowledge base</h2>
                <p className="muted">
                  {Object.keys(kb).length} rules and {allSymptoms.length}{" "}
                  symptoms active in the knowledge base. Click any section to
                  expand details.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAllKbExpanded(!allKbExpanded)}
              >
                {allKbExpanded
                  ? "Collapse all disease cards"
                  : "Expand all disease cards"}
              </button>
            </div>

            <div className="toolbar">
              <input
                type="search"
                aria-label="Search disease rules"
                placeholder="Search disease, symptom, or category…"
                value={kbSearch}
                onChange={(e) => setKbSearch(e.target.value)}
              />
            </div>

            <div className="kb-grid">
              {filteredKbEntries.length === 0 ? (
                <p className="muted">No rules match your search.</p>
              ) : (
                filteredKbEntries.map(([n, d]) => (
                  <article key={n} className="card">
                    <div className="row">
                      <span className="badge">{d.category}</span>
                      <span className="subtle">
                        {d.severity}
                        {d.emergency ? " · Urgent" : ""}
                      </span>
                    </div>
                    <h3 style={{ marginTop: 12 }}>{n}</h3>
                    <p className="subtle">{d.description}</p>
                    <details open={allKbExpanded}>
                      <summary>
                        Expand rule &amp; symptom weights (
                        {Object.keys(d.symptoms).length})
                      </summary>
                      <p className="kb-rule">
                        IF {d.required.map(label).join(" AND ")} → {n}
                      </p>
                      <div className="tags">
                        {Object.entries(d.symptoms).map(([s, w]) => (
                          <span
                            key={s}
                            className={`tag ${
                              d.required.includes(s) ? "good" : ""
                            }`}
                          >
                            {label(s)} · {w}
                            {d.required.includes(s) ? " (req)" : ""}
                          </span>
                        ))}
                      </div>
                    </details>
                    <details open={allKbExpanded}>
                      <summary>Expand treatment &amp; precautions</summary>
                      <p className="subtle">
                        <strong>Treatment:</strong> {d.treatment}
                      </p>
                      <p className="subtle">
                        <strong>Precaution:</strong> {d.precaution}
                      </p>
                      <button
                        type="button"
                        onClick={() => handleLoadDiseaseToWorkspace(n)}
                        style={{
                          width: "100%",
                          marginTop: 6,
                          minHeight: 36,
                          fontSize: 13,
                        }}
                      >
                        Load required facts in workspace →
                      </button>
                    </details>
                  </article>
                ))
              )}
            </div>
          </section>
        )}

        {activeTab === "logs" && (
          <section role="tabpanel">
            <div className="card">
              <div className="row">
                <div>
                  <h2>Persistent evaluation history</h2>
                  <p className="muted">
                    Every rule evaluation is recorded with its timestamp,
                    present/absent facts, and top candidate match. Expand any
                    log entry to inspect or restore it.
                  </p>
                </div>
                <button type="button" onClick={handleClearLogs}>
                  Clear history
                </button>
              </div>
              <div style={{ marginTop: 16 }}>
                {evaluationLogs.length === 0 ? (
                  <div className="empty">
                    <p className="muted">
                      No evaluations recorded yet. Run an evaluation in the
                      Symptom Workspace to log results.
                    </p>
                  </div>
                ) : (
                  evaluationLogs.map((log, idx) => (
                    <details
                      key={log.id || idx}
                      className="expand-panel"
                      open={idx === 0}
                    >
                      <summary>
                        #{log.id} · {log.timestamp} — Top Match:{" "}
                        {log.top_disease} ({Number(log.top_score).toFixed(1)}%)
                      </summary>
                      <div className="expand-panel-body">
                        <p className="subtle">
                          Candidates matched:{" "}
                          <strong>{log.candidate_count}</strong>
                        </p>
                        <p className="subtle">
                          Present facts ({(log.present_facts || []).length}):
                        </p>
                        <div className="tags">
                          {(log.present_facts || []).map((s) => (
                            <span key={s} className="tag good">
                              ✓ {label(s)}
                            </span>
                          ))}
                        </div>
                        {log.absent_facts && log.absent_facts.length > 0 && (
                          <>
                            <p className="subtle">Explicitly absent facts:</p>
                            <div className="tags">
                              {log.absent_facts.map((s) => (
                                <span key={s} className="tag warn">
                                  ✗ {label(s)}
                                </span>
                              ))}
                            </div>
                          </>
                        )}
                        <button
                          type="button"
                          onClick={() => handleRestoreLog(log)}
                          style={{ minHeight: 36, fontSize: 13 }}
                        >
                          Restore this fact set in workspace →
                        </button>
                      </div>
                    </details>
                  ))
                )}
              </div>
            </div>
          </section>
        )}

        {activeTab === "method" && (
          <section role="tabpanel">
            <div className="card intro">
              <h2>Explainable by construction</h2>
              <p className="muted">
                This full-stack React system combines classical knowledge-based
                rule evaluation with a RESTful Python + SQLite backend and
                declarative component state.
              </p>
              <div className="method">
                <h3>01 / Facts, weights, and expandable entities</h3>
                <p>
                  Each disease has weighted symptom facts and required premises
                  stored in normalized relational tables. Expanding any symptom
                  or disease reveals its underlying weights, clinical guidance,
                  and cross-rule relationships.
                </p>
              </div>
              <div className="method">
                <h3>02 / Forward rule evaluation</h3>
                <p>
                  A single pass evaluates every disease rule. All required facts
                  must be present before its implication fires. Ranking also
                  includes partial overlaps; a partial match is not an inferred
                  disease.
                </p>
                <pre className="logic">
                  {`score = 100 × matched weight / total weight
if any required fact is missing: score ×= 0.60`}
                </pre>
              </div>
              <div className="method">
                <h3>
                  03 / Backward premise checks &amp; optional symptom expansion
                </h3>
                <p>
                  Choose a hypothesis and inspect both its missing required
                  premises and its unmatched optional symptoms. Answering
                  unknown premises or toggling optional symptoms recomputes the
                  ranking in real time.
                </p>
              </div>
              <div className="method">
                <h3>
                  04 / Consistency checks &amp; expandable contradiction pairs
                </h3>
                <p>
                  Contradictory inputs block evaluation until corrected. Active
                  contradiction pairs and red-flag safety warning symptoms can
                  be inspected and expanded below.
                </p>
                <details className="expand-panel" open>
                  <summary>
                    Inspect active contradiction pairs &amp; safety triggers
                  </summary>
                  <div className="expand-panel-body">
                    <p>
                      <strong>
                        Active Contradiction Pairs ({contradictions.length}):
                      </strong>
                    </p>
                    <div className="tags">
                      {contradictions.map((p, i) => (
                        <span key={i} className="tag warn">
                          {label(p[0])} ↔ {label(p[1])}
                        </span>
                      ))}
                    </div>
                    <p>
                      <strong>
                        Red-Flag Triage Warning Facts ({warningFacts.length}):
                      </strong>
                    </p>
                    <div className="tags">
                      {warningFacts.map((w) => (
                        <span
                          key={w}
                          className="tag"
                          style={{ color: "var(--red)" }}
                        >
                          ! {label(w)}
                        </span>
                      ))}
                    </div>
                  </div>
                </details>
              </div>
            </div>
          </section>
        )}
      </main>

      <aside className="notice">
        <strong>For learning, not diagnosis.</strong> Do not use this demo to
        make healthcare decisions or delay care. If you have severe breathing
        difficulty, chest pain, confusion, fainting, or another medical
        emergency, contact local emergency services immediately.
      </aside>

      <footer>
        <span>MEDIXAI / Full-Stack Dynamic React Expert System</span>
        <span>CS23531 Web Programming &amp; CS23533 FOAI</span>
      </footer>
    </div>
  );
}
