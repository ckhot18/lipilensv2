import { useEffect, useRef, useState } from "react";
import {
  getManuscript,
  imgUrl,
  listManuscripts,
  verifyTranscription,
} from "../api/client";

const PAGE = 8;
const FILTERS = [
  ["all", "All"],
  ["verified", "Verified"],
  ["review", "Needs Review"],
];

export default function Library({ initialQuery = "" }) {
  const [query, setQuery] = useState(initialQuery);
  const [debounced, setDebounced] = useState(initialQuery);
  const [filter, setFilter] = useState("all");
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setDebounced(query);
      setOffset(0);
    }, 400);
    return () => clearTimeout(timer.current);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await listManuscripts({
          search: debounced || undefined,
          verifiedOnly: filter === "verified" ? true : undefined,
          limit: PAGE,
          offset,
        });
        let visible = rows;
        if (filter === "review") visible = rows.filter((m) => !m.verified);
        if (!cancelled) {
          setItems((prev) => (offset === 0 ? visible : [...prev, ...visible]));
          setHasMore(rows.length === PAGE);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();
    return () => { cancelled = true; };
  }, [debounced, filter, offset]);

  async function openDetail(id) {
    setError("");
    try {
      const ms = await getManuscript(id);
      setSelected(ms);
      setDraft(ms.transcription?.verified_transcription ||
               ms.transcription?.ai_transcription || "");
      setEditing(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveVerification() {
    if (!selected?.transcription || !draft.trim()) return;
    try {
      await verifyTranscription(selected.transcription.id, draft.trim());
      const ms = await getManuscript(selected.id);
      setSelected(ms);
      setEditing(false);
      setOffset(0);
    } catch (err) {
      setError(err.message);
    }
  }

  const tr = selected?.transcription;

  return (
    <section className="page">
      <p className="kicker">EXPLORE · SEARCH · LEARN</p>
      <h2 className="display-sm">Manuscript Library</h2>
      <p className="subtitle">
        A growing collection of historical documents, restored and transcribed
        using AI. Browse, search, and explore India&apos;s written heritage.
      </p>

      <div className="chips">
        {FILTERS.map(([key, label]) => (
            <button
              key={key}
              className={filter === key ? "chip active" : "chip"}
              onClick={() => { setFilter(key); setOffset(0); }}
            >
            {label}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by title, keyword, identifier…"
        />
      </div>
      {error && <p className="error">{error}</p>}

      {!selected && (
        <>
          <div className="grid cards4">
            {items.map((m) => (
              <button key={m.id} className="mscard" onClick={() => openDetail(m.id)}>
                {m.thumbnail_url && (
                  <img className="mscard-img" src={imgUrl(m.thumbnail_url)} alt={m.title} loading="lazy" />
                )}
                <span className={m.verified ? "badge ok floating" : "badge warn floating"}>
                  {m.verified ? "Verified" : "Needs Review"}
                </span>
                <span className="mscard-title">{m.title}</span>
                <span className="muted small">#{m.id} · {m.identifier || m.status}</span>
              </button>
            ))}
          </div>
          {items.length === 0 && <p className="muted">No manuscripts found.</p>}
          {hasMore && items.length > 0 && (
            <div style={{ textAlign: "center", marginTop: 16 }}>
              <button className="ghost" onClick={() => setOffset((o) => o + PAGE)}>
                Load More ↓
              </button>
            </div>
          )}
        </>
      )}

      {selected && (
        <div className="card">
          <button className="link" onClick={() => setSelected(null)}>
            ← Back to list
          </button>
          <h3>
            #{selected.id} {selected.title}{" "}
            <span className={selected.status === "verified" ? "badge ok" : "badge warn"}>
              {selected.status === "verified" ? "Verified" : "AI draft — pending review"}
            </span>
          </h3>
          <div className="imgrow">
            <figure>
              <figcaption>Original</figcaption>
              <img src={imgUrl(selected.original_image_url)} alt="Original manuscript" />
            </figure>
            <figure>
              <figcaption>Restored</figcaption>
              <img src={imgUrl(selected.restored_image_url)} alt="Restored manuscript" />
            </figure>
          </div>
          <h4>AI transcription (immutable draft)</h4>
          <p className="transcript">{tr?.ai_transcription || "—"}</p>
          <h4>Verified transcription</h4>
          {editing ? (
            <>
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={6} />
              <div className="btnrow">
                <button onClick={saveVerification}>Save verification</button>
                <button className="ghost" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </>
          ) : (
            <>
              <p className="transcript">{tr?.verified_transcription || "Not verified yet."}</p>
              {tr && (
                <button onClick={() => setEditing(true)}>
                  {tr.verified_transcription ? "Re-edit verification" : "Verify now"}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
