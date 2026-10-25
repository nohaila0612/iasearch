import { useState } from "react";
import "./App.css";

type Result = { line: string; score: number; rerank_score: number; cluster?: string; label?: string };

const API = "http://localhost:8000/search";
const COLORS = ["#0f9d8a", "#6c4cf1", "#e8590c", "#2276d2", "#c2255c"];
const EXAMPLES = ["travaux de construction", "matériel informatique", "maîtrise d’œuvre"];

const clusterNumber = (c?: string) => parseInt((c ?? "").replace(/\D/g, ""), 10) || 1;

function splitLine(line: string) {
  const i = line.indexOf(";");
  if (i > 0 && i < 20) return { ref: line.slice(0, i).trim(), title: line.slice(i + 1).trim() };
  return { ref: null, title: line };
}

function Highlight({ text, query }: { text: string; query: string }) {
  const words = query.split(/\s+/).filter((w) => w.length > 3).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (!words.length) return <>{text}</>;
  const parts = text.split(new RegExp("(" + words.join("|") + ")", "gi"));
  return <>{parts.map((p, i) => (i % 2 ? <mark key={i}>{p}</mark> : p))}</>;
}

function Card({ r, query }: { r: Result; query: string }) {
  const n = clusterNumber(r.cluster);
  const color = COLORS[(n - 1) % COLORS.length];
  const pct = Math.round(r.rerank_score * 100);
  const { ref, title } = splitLine(r.line);
  return (
    <article className="res" style={{ ["--c" as string]: color }}>
      <div className="ring">
        <svg width="72" height="72" viewBox="0 0 72 72">
          <circle className="bg" cx="36" cy="36" r="30" />
          <circle className="fg" cx="36" cy="36" r="30" style={{ strokeDashoffset: 188.5 * (1 - r.rerank_score) }} />
        </svg>
        <span>{pct}%</span>
      </div>
      <div>
        <div className="tags">
          {ref && <span className="ref">{ref}</span>}
          <span className="cl">{r.label ?? `Groupe ${n}`}</span>
        </div>
        <p className="t"><Highlight text={title} query={query} /></p>
      </div>
    </article>
  );
}

function App() {
  const [query, setQuery] = useState("");
  const [asked, setAsked] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const search = async (q: string = query) => {
    if (!q.trim()) return;
    setQuery(q);
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      if (!r.ok) throw new Error("Le serveur a répondu avec l’erreur " + r.status);
      const data = await r.json();
      setResults(data.results);
      setAsked(q);
      setSearched(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="hero">
        <div className="wrap">
          <div className="logo"><b>◆</b> IA Search</div>
          <h1>Trouvez le bon marché en une phrase.</h1>
          <p>Décrivez votre besoin avec vos propres mots. L’IA explore les documents et classe les plus pertinents en premier.</p>
        </div>
      </header>

      <div className="search">
        <div className="box" role="search">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="Ex. : construction d’un gymnase"
            aria-label="Votre recherche"
          />
          <button onClick={() => search()} disabled={loading}>{loading ? "…" : "Rechercher"}</button>
        </div>
        <div className="chips">
          {EXAMPLES.map((e) => <button key={e} onClick={() => search(e)}>{e}</button>)}
        </div>
      </div>

      <main className="results" aria-live="polite">
        {loading && <><div className="bar">Recherche et classement en cours…</div>{[0, 1, 2].map((i) => <div className="sk" key={i} />)}</>}
        {!loading && error && <div className="error">{error}. Vérifiez que le backend tourne sur localhost:8000.</div>}
        {!loading && !error && !searched && <div className="empty">Saisissez une recherche ou choisissez un exemple ci-dessus.</div>}
        {!loading && !error && searched && results.length === 0 && <div className="empty">Aucun résultat pour « {asked} ». Essayez avec d’autres mots.</div>}
        {!loading && !error && results.length > 0 && (
          <>
            <div className="bar"><strong>{results.length} résultats</strong> pour « {asked} »</div>
            {results.map((r, i) => <Card key={i} r={r} query={asked} />)}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
