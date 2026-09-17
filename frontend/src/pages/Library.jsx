import { useCallback, useEffect, useRef, useState } from "react";
import {
  getManuscript,
  imgUrl,
  listManuscripts,
  verifyTranscription,
} from "../api/client";

export default function Library() {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setDebounced(query), 400);
    return () => clearTimeout(timer.current);
  }, [query]);

  const refresh = useCallback(async () => {
    setError("");
    try {
      const rows = await listManuscripts({
        search: debounced || undefined,
        verifiedOnly,
      });
      setItems(rows);
    } catch (err) {
      setError(err.message);
    }
  }, [debounced, verifiedOnly]);

  useEffect(() => {
    refresh();
  }, [refresh]);

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
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  const tr = selected?.transcription;

  return (
    <section className="page">
      <h2>My Library</h2>
      <div className="toolbar">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search title, identifier, or text…"
        />
        <label className="check">
          <input
            type="checkbox"
            checked={verifiedOnly}
            onChange={(e) => setVerifiedOnly(e.target.checked)}
          />
          Verified only
        </label>
      </div>
      {error && <p className="error">{error}</p>}

      {!selected && (
        <ul className="list">
          {items.map((m) => (
            <li key={m.id}>
              <button className="rowlink" onClick={() => openDetail(m.id)}>
                <strong>#{m.id} {m.title}</strong>
                <span className={m.verified ? "badge ok" : "badge warn"}>
                  {m.verified ? "Verified" : "Pending review"}
                </span>
              </button>
            </li>
          ))}
          {items.length === 0 && <li className="muted">No manuscripts found.</li>}
        </ul>
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
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={6}
              />
              <div className="btnrow">
                <button onClick={saveVerification}>Save verification</button>
                <button className="ghost" onClick={() => setEditing(false)}>
                  Cancel
                </button>
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
