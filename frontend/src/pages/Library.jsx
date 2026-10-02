import { useEffect, useRef, useState } from "react";
import CompareSlider from "../components/CompareSlider.jsx";
import TextPanel from "../components/TextPanel.jsx";
import { IconArrowLeft, IconShieldCheck } from "../components/Icons.jsx";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const timer = useRef(null);
  const lastQuery = useRef(initialQuery);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      if (query === lastQuery.current) return;
      lastQuery.current = query;
      setDebounced(query);
      setOffset(0);
      setLoading(true);
    }, 350);
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
        const visible = filter === "review" ? rows.filter((m) => !m.verified) : rows;
        if (cancelled) return;
        setItems((prev) => (offset === 0 ? visible : [...prev, ...visible]));
        setHasMore(rows.length === PAGE);
        setError("");
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [debounced, filter, offset]);

  async function openDetail(id) {
    setError("");
    try {
      const ms = await getManuscript(id);
      setSelected(ms);
      setDraft(ms.transcription?.verified_transcription || ms.transcription?.ai_transcription || "");
      setEditing(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveVerification() {
    const text = draft.trim();
    if (!selected?.transcription || !text) {
      setError("Verified text must not be empty.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await verifyTranscription(selected.transcription.id, text);
      setSelected(await getManuscript(selected.id));
      setEditing(false);
      setOffset(0);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const tr = selected?.transcription;

  if (selected) {
    return (
      <>
        <div className="analysis-head">
          <h1 className="h1">
            #{selected.id} {selected.title}
            {tr?.verified_transcription ? (
              <span className="badge ok" style={{ marginLeft: 8 }}>
                <IconShieldCheck style={{ width: 11, height: 11 }} />
                Verified
              </span>
            ) : (
              <span className="badge warn" style={{ marginLeft: 8 }}>
                Needs review
              </span>
            )}
          </h1>
          <button type="button" className="btn ghost sm" onClick={() => setSelected(null)}>
            <IconArrowLeft style={{ width: 13, height: 13 }} />
            Back to library
          </button>
        </div>

        <div className="analysis">
          <CompareSlider
            original={imgUrl(selected.original_image_url)}
            restored={imgUrl(selected.restored_image_url)}
            rightLabel="Restored"
          />
          <div className="analysis-side">
            <TextPanel
              title="Digitized Text"
              value={tr?.ai_transcription}
              badge={<span className="badge accent" style={{ marginLeft: 8 }}>AI draft</span>}
            />
            <TextPanel
              title="Verified Transcription"
              value={editing ? undefined : tr?.verified_transcription}
              latin
            >
              {editing ? (
                <>
                  <textarea
                    className="textarea"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    rows={6}
                    aria-label="Verified transcription"
                  />
                  <div className="btnrow" style={{ marginTop: 10 }}>
                    <button
                      type="button"
                      className="btn sm"
                      onClick={saveVerification}
                      disabled={saving}
                    >
                      {saving ? "Saving…" : "Save verification"}
                    </button>
                    <button
                      type="button"
                      className="btn ghost sm"
                      onClick={() => setEditing(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <div className="btnrow" style={{ marginTop: 10 }}>
                  <button type="button" className="btn sm" onClick={() => setEditing(true)}>
                    {tr?.verified_transcription ? "Re-edit verification" : "Verify now"}
                  </button>
                </div>
              )}
            </TextPanel>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <p className="kicker">Explore · search · learn</p>
      <h1 className="display" style={{ fontSize: 34 }}>
        Manuscript Library
      </h1>
      <p className="lede" style={{ marginBottom: 22 }}>
        A growing collection of historical documents, restored and transcribed
        with AI. Search by title, identifier, place or keyword.
      </p>

      <div className="chips">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={filter === key ? "chip active" : "chip"}
            onClick={() => {
              setFilter(key);
              setOffset(0);
              setLoading(true);
            }}
            aria-pressed={filter === key}
          >
            {label}
          </button>
        ))}
      </div>

      <div style={{ marginBottom: 16 }}>
        <label className="field">
          <span className="dz-sr">Search the library</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title, keyword, identifier…"
          />
        </label>
      </div>

      {error && (
        <p className="notice err" role="alert">
          {error}
        </p>
      )}

      <div className="grid-cards">
        {items.map((m) => (
          <button
            key={m.id}
            type="button"
            className="mscard"
            onClick={() => openDetail(m.id)}
          >
            {m.thumbnail_url && (
              <img src={imgUrl(m.thumbnail_url)} alt="" loading="lazy" />
            )}
            <span className={m.verified ? "badge ok" : "badge warn"}>
              {m.verified ? "Verified" : "Needs review"}
            </span>
            <span className="mscard-title">{m.title}</span>
            <span className="mscard-meta">
              #{m.id}
              {m.identifier ? ` · ${m.identifier}` : ""}
            </span>
          </button>
        ))}
      </div>

      {items.length === 0 && !loading && (
        <p className="muted">No manuscripts match this search.</p>
      )}

      {loading && (
        <p className="muted" role="status">
          <span className="spinner" /> Loading manuscripts…
        </p>
      )}

      {hasMore && items.length > 0 && (
        <div className="btnrow" style={{ justifyContent: "center", marginTop: 18 }}>
          <button
            type="button"
            className="btn ghost"
            onClick={() => {
              setOffset((o) => o + PAGE);
              setLoading(true);
            }}
            disabled={loading}
          >
            Load more
          </button>
        </div>
      )}
    </>
  );
}