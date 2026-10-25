import { useState } from "react";

type Result = { line: string; score: number };

function App() {
  const [query, setQuery] = useState("");
  const [cluster, setCluster] = useState<string | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const r = await fetch("http://localhost:8000/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await r.json();
      setCluster(data.cluster);
      setResults(data.results);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "2rem auto", textAlign: "left" }}>
      <h1>IA Search</h1>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && search()}
        placeholder="Votre recherche..."
        style={{ width: "70%", padding: 8 }}
      />
      <button onClick={search} style={{ marginLeft: 8, padding: 8 }}>
        Search
      </button>
      {loading && <p>Recherche en cours...</p>}
      {cluster && <p>Cluster : {cluster}</p>}
      <ul>
        {results.map((r, i) => (
          <li key={i}>
            {r.line} <small>({r.score.toFixed(2)})</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
