import { useState, useRef } from "react";

// ── Sample data (remplacez par votre results.json) ───────────────────────
const SAMPLE_DATA = {
  meta: {
    generated_at: new Date().toISOString(),
    agents: ["Claude", "GPT", "Gemini", "Local"],
    questions: 3,
  },
  results: [
    {
      id: "q1",
      question: "Explique le concept de récursivité en programmation en 3 phrases.",
      expected: null,
      agents: {
        Claude:  { score: 9,  latency_s: 1.2, answer: "La récursivité est une technique où une fonction s'appelle elle-même pour résoudre un problème plus petit. Chaque appel réduit le problème jusqu'à atteindre un cas de base qui stoppe la récursion. C'est utilisé par exemple dans les algorithmes de tri ou le parcours d'arbres.", justification: "Réponse précise, concise et bien structurée." },
        GPT:     { score: 8,  latency_s: 1.8, answer: "La récursivité consiste pour une fonction à s'appeler elle-même. Elle nécessite un cas de base pour éviter une boucle infinie. On l'utilise pour des structures comme les arbres ou les fractales.", justification: "Correct mais légèrement moins détaillé." },
        Gemini:  { score: 7,  latency_s: 2.1, answer: "Une fonction récursive s'appelle elle-même. Il faut toujours un cas d'arrêt. Exemples : factorielle, Fibonacci.", justification: "Réponse valide mais trop brève." },
        Local:   { score: 6,  latency_s: 3.4, answer: "La récursivité c'est quand une fonction se rappelle elle-même. Ça peut causer des problèmes si pas de condition d'arrêt. Utilisé en algorithmique.", justification: "Approximatif, manque de précision." },
      },
    },
    {
      id: "q2",
      question: "Quelle est la complexité temporelle d'un quicksort dans le pire cas ?",
      expected: "O(n²)",
      agents: {
        Claude:  { score: 10, latency_s: 0.9, answer: "O(n²)", justification: "Réponse parfaitement exacte." },
        GPT:     { score: 10, latency_s: 1.1, answer: "O(n²) dans le pire cas, O(n log n) en moyenne.", justification: "Correct avec précision supplémentaire." },
        Gemini:  { score: 10, latency_s: 1.4, answer: "La complexité dans le pire cas du quicksort est O(n²).", justification: "Exact." },
        Local:   { score: 5,  latency_s: 2.9, answer: "O(n log n)", justification: "Confusion avec le cas moyen." },
      },
    },
    {
      id: "q3",
      question: "Donne-moi un exemple de code Python pour inverser une liste.",
      expected: null,
      agents: {
        Claude:  { score: 9,  latency_s: 1.5, answer: "my_list = [1, 2, 3]\nreversed_list = my_list[::-1]  # Slicing\n# Ou: my_list.reverse()  # In-place", justification: "Deux méthodes présentées clairement." },
        GPT:     { score: 8,  latency_s: 2.0, answer: "lst = [1, 2, 3, 4]\nlst.reverse()\nprint(lst)  # [4, 3, 2, 1]", justification: "Correct mais une seule méthode." },
        Gemini:  { score: 8,  latency_s: 1.9, answer: "liste = [1, 2, 3]\nprint(liste[::-1])", justification: "Concis et correct." },
        Local:   { score: 7,  latency_s: 4.1, answer: "def reverse_list(l):\n  return l[::-1]\nprint(reverse_list([1,2,3]))", justification: "Fonctionne, style verbeux." },
      },
    },
  ],
};

// ── Couleurs par agent ───────────────────────────────────────────────────
const AGENT_COLORS = {
  Claude: "#e8a87c",
  GPT:    "#74c69d",
  Gemini: "#74b3f5",
  Local:  "#c084fc",
};

const scoreColor = (s) => {
  if (s >= 9)  return "#74c69d";
  if (s >= 7)  return "#e8a87c";
  if (s >= 5)  return "#fbbf24";
  return "#f87171";
};

// ── Mini bar ─────────────────────────────────────────────────────────────
const ScoreBar = ({ score, agent }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
    <div style={{
      width: 120, height: 6, background: "#1e1e2e", borderRadius: 3, overflow: "hidden",
    }}>
      <div style={{
        width: `${(score / 10) * 100}%`, height: "100%",
        background: AGENT_COLORS[agent] || scoreColor(score),
        borderRadius: 3, transition: "width 0.6s ease",
      }} />
    </div>
    <span style={{ color: scoreColor(score), fontFamily: "monospace", fontSize: 13, fontWeight: 700 }}>
      {score}/10
    </span>
  </div>
);

// ── Modal réponse ────────────────────────────────────────────────────────
const Modal = ({ cell, onClose }) => {
  if (!cell) return null;
  return (
    <div onClick={onClose} style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: "#16162a", border: `1px solid ${AGENT_COLORS[cell.agent] || "#333"}`,
        borderRadius: 12, padding: 28, maxWidth: 580, width: "90%",
        boxShadow: `0 0 40px ${AGENT_COLORS[cell.agent] || "#333"}44`,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <span style={{ color: AGENT_COLORS[cell.agent], fontWeight: 700, fontSize: 15 }}>{cell.agent}</span>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#666", cursor: "pointer", fontSize: 20 }}>✕</button>
        </div>
        <p style={{ color: "#888", fontSize: 12, marginBottom: 10 }}>{cell.question}</p>
        <pre style={{
          background: "#0d0d1a", borderRadius: 8, padding: 14, color: "#e2e2f0",
          fontSize: 13, whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 220, overflowY: "auto",
          border: "1px solid #2a2a3e",
        }}>{cell.answer}</pre>
        <div style={{ marginTop: 12, padding: "10px 14px", background: "#1e1e2e", borderRadius: 8, borderLeft: `3px solid ${AGENT_COLORS[cell.agent]}` }}>
          <span style={{ color: "#888", fontSize: 11, display: "block", marginBottom: 4 }}>JUSTIFICATION DU JUGE IA</span>
          <span style={{ color: "#ccc", fontSize: 13 }}>{cell.justification}</span>
        </div>
        <div style={{ display: "flex", gap: 16, marginTop: 14 }}>
          <span style={{ color: "#888", fontSize: 12 }}>⏱ {cell.latency_s}s</span>
          <span style={{ color: scoreColor(cell.score), fontWeight: 700 }}>Score : {cell.score}/10</span>
        </div>
      </div>
    </div>
  );
};

// ── Composant principal ──────────────────────────────────────────────────
export default function BenchmarkDashboard() {
  const [data, setData] = useState(SAMPLE_DATA);
  const [modal, setModal] = useState(null);
  const [activeTab, setActiveTab] = useState("table");
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef();

  const agents = data.meta.agents;
  const results = data.results;

  // Moyennes
  const averages = {};
  agents.forEach(a => {
    const scores = results.map(r => r.agents[a]?.score).filter(s => s != null && s >= 0);
    const lats   = results.map(r => r.agents[a]?.latency_s).filter(Boolean);
    averages[a] = {
      score: scores.length ? (scores.reduce((x, y) => x + y, 0) / scores.length).toFixed(1) : "N/A",
      latency: lats.length ? (lats.reduce((x, y) => x + y, 0) / lats.length).toFixed(2) : "N/A",
    };
  });

  const loadJSON = (text) => {
    try { setData(JSON.parse(text)); } catch { alert("JSON invalide"); }
  };

  const handleFile = (f) => {
    if (!f) return;
    const r = new FileReader();
    r.onload = e => loadJSON(e.target.result);
    r.readAsText(f);
  };

  const exportCSV = () => {
    const rows = [["Question", ...agents.flatMap(a => [`${a}_score`, `${a}_latency`])]];
    results.forEach(r => {
      rows.push([r.question, ...agents.flatMap(a => [r.agents[a]?.score ?? "", r.agents[a]?.latency_s ?? ""])]);
    });
    const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "benchmark_export.csv"; a.click();
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "benchmark_export.json"; a.click();
  };

  const styles = {
    root: {
      minHeight: "100vh", background: "#0d0d1a", color: "#e2e2f0",
      fontFamily: "'DM Mono', 'Fira Code', monospace",
      padding: "24px 20px",
    },
    header: { marginBottom: 28 },
    title: { fontSize: 22, fontWeight: 700, color: "#fff", letterSpacing: 1, margin: 0 },
    subtitle: { fontSize: 12, color: "#555", marginTop: 4, letterSpacing: 2 },
    topBar: { display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 20 },
    btn: {
      padding: "7px 14px", borderRadius: 6, border: "1px solid #2a2a3e",
      background: "#16162a", color: "#aaa", fontSize: 12, cursor: "pointer",
      fontFamily: "inherit", letterSpacing: 0.5,
    },
    tab: (active) => ({
      padding: "7px 16px", borderRadius: 6, border: "none",
      background: active ? "#e8a87c" : "#1e1e2e", color: active ? "#0d0d1a" : "#888",
      fontSize: 12, cursor: "pointer", fontFamily: "inherit", fontWeight: active ? 700 : 400,
    }),
    card: {
      background: "#16162a", border: "1px solid #2a2a3e", borderRadius: 10,
      padding: "16px 20px", marginBottom: 16,
    },
    drop: {
      border: `2px dashed ${dragOver ? "#e8a87c" : "#2a2a3e"}`,
      borderRadius: 10, padding: "28px 20px", textAlign: "center",
      cursor: "pointer", marginBottom: 20, background: dragOver ? "#1a1a2e" : "transparent",
      transition: "all 0.2s",
    },
    table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
    th: { padding: "10px 12px", textAlign: "left", color: "#555", fontSize: 11, letterSpacing: 1.5, borderBottom: "1px solid #2a2a3e" },
    td: { padding: "12px 12px", borderBottom: "1px solid #1a1a2e", verticalAlign: "top" },
  };

  return (
    <div style={styles.root}>
      <Modal cell={modal} onClose={() => setModal(null)} />

      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>⚡ BENCHMARK MULTI-AGENTS</h1>
        <p style={styles.subtitle}>
          {data.meta.questions} QUESTIONS · {agents.length} AGENTS · {new Date(data.meta.generated_at).toLocaleString("fr-FR")}
        </p>
      </div>

      {/* Top bar */}
      <div style={styles.topBar}>
        <button style={styles.tab(activeTab === "table")} onClick={() => setActiveTab("table")}>📊 Tableau</button>
        <button style={styles.tab(activeTab === "summary")} onClick={() => setActiveTab("summary")}>🏆 Résumé</button>
        <button style={styles.tab(activeTab === "import")} onClick={() => setActiveTab("import")}>📂 Importer JSON</button>
        <div style={{ flex: 1 }} />
        <button style={styles.btn} onClick={exportCSV}>⬇ CSV</button>
        <button style={styles.btn} onClick={exportJSON}>⬇ JSON</button>
      </div>

      {/* ── TAB : RÉSUMÉ ─────────────────────────────────────── */}
      {activeTab === "summary" && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginBottom: 20 }}>
            {agents.map(a => (
              <div key={a} style={{
                ...styles.card,
                borderColor: AGENT_COLORS[a] || "#333",
                boxShadow: `0 0 20px ${AGENT_COLORS[a] || "#333"}22`,
              }}>
                <div style={{ color: AGENT_COLORS[a], fontWeight: 700, fontSize: 13, marginBottom: 8 }}>{a}</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: scoreColor(parseFloat(averages[a].score)) }}>
                  {averages[a].score}
                  <span style={{ fontSize: 14, color: "#555" }}>/10</span>
                </div>
                <div style={{ color: "#555", fontSize: 11, marginTop: 4 }}>⏱ {averages[a].latency}s moy.</div>
                <div style={{ marginTop: 10 }}>
                  <div style={{ height: 4, background: "#1e1e2e", borderRadius: 2 }}>
                    <div style={{
                      height: "100%", width: `${(parseFloat(averages[a].score) / 10) * 100}%`,
                      background: AGENT_COLORS[a], borderRadius: 2, transition: "width 0.8s ease",
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Scores par question */}
          <div style={styles.card}>
            <div style={{ color: "#555", fontSize: 11, letterSpacing: 1.5, marginBottom: 14 }}>SCORES PAR QUESTION</div>
            {results.map((r, i) => (
              <div key={r.id} style={{ marginBottom: 16 }}>
                <div style={{ color: "#888", fontSize: 12, marginBottom: 8 }}>
                  <span style={{ color: "#e8a87c" }}>#{i + 1}</span> {r.question.slice(0, 70)}{r.question.length > 70 ? "…" : ""}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  {agents.map(a => (
                    <div key={a} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ color: AGENT_COLORS[a], fontSize: 11, width: 60 }}>{a}</span>
                      <ScoreBar score={r.agents[a]?.score ?? 0} agent={a} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TAB : TABLEAU ─────────────────────────────────────── */}
      {activeTab === "table" && (
        <div style={{ overflowX: "auto" }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={{ ...styles.th, width: 30 }}>#</th>
                <th style={{ ...styles.th, minWidth: 220 }}>QUESTION</th>
                {agents.map(a => (
                  <th key={a} style={{ ...styles.th, minWidth: 160, color: AGENT_COLORS[a] || "#555" }}>{a.toUpperCase()}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={r.id} style={{ transition: "background 0.15s" }}
                  onMouseEnter={e => e.currentTarget.style.background = "#16162a"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                >
                  <td style={{ ...styles.td, color: "#444", fontSize: 11 }}>{i + 1}</td>
                  <td style={{ ...styles.td }}>
                    <div style={{ color: "#ccc", fontSize: 12, lineHeight: 1.5 }}>{r.question}</div>
                    {r.expected && (
                      <div style={{ marginTop: 5, color: "#555", fontSize: 11 }}>
                        attendu : <span style={{ color: "#74c69d" }}>{r.expected}</span>
                      </div>
                    )}
                  </td>
                  {agents.map(a => {
                    const d = r.agents[a];
                    if (!d) return <td key={a} style={styles.td}><span style={{ color: "#333" }}>—</span></td>;
                    return (
                      <td key={a} style={styles.td}>
                        <ScoreBar score={d.score} agent={a} />
                        <div style={{ color: "#444", fontSize: 11, marginTop: 4 }}>⏱ {d.latency_s}s</div>
                        <button
                          onClick={() => setModal({ ...d, agent: a, question: r.question })}
                          style={{
                            marginTop: 6, padding: "3px 10px", borderRadius: 4,
                            background: "none", border: `1px solid ${AGENT_COLORS[a]}44`,
                            color: AGENT_COLORS[a] || "#888", fontSize: 11, cursor: "pointer",
                            fontFamily: "inherit",
                          }}
                        >voir réponse →</button>
                      </td>
                    );
                  })}
                </tr>
              ))}
              {/* Ligne moyennes */}
              <tr style={{ background: "#0d0d1a" }}>
                <td style={{ ...styles.td }} />
                <td style={{ ...styles.td, color: "#555", fontSize: 11, letterSpacing: 1 }}>SCORE MOYEN</td>
                {agents.map(a => (
                  <td key={a} style={styles.td}>
                    <span style={{ color: scoreColor(parseFloat(averages[a].score)), fontWeight: 700, fontSize: 16 }}>
                      {averages[a].score}
                    </span>
                    <span style={{ color: "#444" }}>/10</span>
                    <div style={{ color: "#444", fontSize: 11, marginTop: 2 }}>⏱ {averages[a].latency}s moy.</div>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* ── TAB : IMPORT ─────────────────────────────────────── */}
      {activeTab === "import" && (
        <div>
          <div
            style={styles.drop}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
            onClick={() => fileRef.current.click()}
          >
            <div style={{ fontSize: 32, marginBottom: 8 }}>📂</div>
            <div style={{ color: "#888", fontSize: 13 }}>Glissez votre <code style={{ color: "#e8a87c" }}>results.json</code> ici</div>
            <div style={{ color: "#444", fontSize: 11, marginTop: 4 }}>ou cliquez pour parcourir</div>
            <input ref={fileRef} type="file" accept=".json" style={{ display: "none" }}
              onChange={e => handleFile(e.target.files[0])} />
          </div>
          <div style={styles.card}>
            <div style={{ color: "#555", fontSize: 11, letterSpacing: 1.5, marginBottom: 10 }}>OU COLLEZ VOTRE JSON</div>
            <textarea
              placeholder='{"meta": {...}, "results": [...]}'
              style={{
                width: "100%", minHeight: 160, background: "#0d0d1a", border: "1px solid #2a2a3e",
                borderRadius: 8, color: "#e2e2f0", padding: 12, fontFamily: "monospace", fontSize: 12,
                resize: "vertical", outline: "none", boxSizing: "border-box",
              }}
              onBlur={e => { if (e.target.value.trim()) loadJSON(e.target.value); }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
