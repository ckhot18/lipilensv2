import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CompareSlider from "../components/CompareSlider.jsx";
import TextPanel from "../components/TextPanel.jsx";
import {
  IconArrowLeft,
  IconBook,
  IconDots,
  IconEye,
  IconGrid,
  IconList,
  IconLock,
  IconSearch,
} from "../components/Icons.jsx";
import {
  getManuscript,
  imgUrl,
  listManuscripts,
  verifyTranscription,
} from "../api/client";

const PAGE = 8;
const FETCH_LIMIT = 200; // backend hard cap; demo archives stay below this

const DATE_RANGES = [
  ["all", "Date range · All time"],
  ["7", "Date range · 7 days"],
  ["30", "Date range · 30 days"],
  ["90", "Date range · 90 days"],
];

function splitStamp(created) {
  if (!created) return { date: "—", time: "" };
  const d = new Date(created);
  if (Number.isNaN(d.getTime())) return { date: "—", time: "" };
  return {
    date: d.toLocaleDateString("en-CA"), // 2025-09-14, per the reference table
    time: d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }),
  };
}

function inRange(created, range) {
  if (!created || range === "all") return true;
  const t = new Date(created).getTime();
  if (Number.isNaN(t)) return true;
  return t >= Date.now() - Number(range) * 86400000;
}

export default function Library({ initialQuery = "", onNavigateTranscribe }) {
  const [query, setQuery] = useState(initialQuery);
  const [debounced, setDebounced] = useState(initialQuery);
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateRange, setDateRange] = useState("all");
  const [view, setView] = useState("list");
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({ total: 0, review: 0, verified: 0 });
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savedNotice, setSavedNotice] = useState(false);
  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const timer = useRef(null);
  const lastQuery = useRef(initialQuery);

  const loadStats = useCallback(async (signal) => {
    try {
      const rows = await listManuscripts({ limit: FETCH_LIMIT });
      if (signal?.cancelled) return;
      const verified = rows.filter((r) => r.verified).length;
      setStats({ total: rows.length, review: rows.length - verified, verified });
    } catch {
      /* stats are cosmetic; the list carries its own error state */
    }
  }, []);

  const loadList = useCallback(async (args, signal) => {
    // Deferred one tick: a loading flag set synchronously inside an effect
    // body would re-render before the fetch even starts.
    queueMicrotask(() => {
      if (!signal?.cancelled) setLoading(true);
    });
    try {
      const rows = await listManuscripts({
        search: args.search || undefined,
        verifiedOnly:
          args.verified === true ? true : args.verified === false ? false : undefined,
        limit: FETCH_LIMIT,
      });
      if (signal?.cancelled) return;
      setItems(rows);
      setError("");
    } catch (err) {
      if (!signal?.cancelled) setError(err.message);
    } finally {
      if (!signal?.cancelled) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const live = { cancelled: false };
    loadStats(live);
    return () => {
      live.cancelled = true;
    };
  }, [loadStats]);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      if (query !== lastQuery.current) {
        lastQuery.current = query;
        setDebounced(query);
        setPage(0);
      }
    }, 300);
    return () => clearTimeout(timer.current);
  }, [query]);

  useEffect(() => {
    const live = { cancelled: false };
    loadList(
      {
        search: debounced,
        verified:
          statusFilter === "verified" ? true : statusFilter === "review" ? false : null,
      },
      live
    );
    return () => {
      live.cancelled = true;
    };
  }, [debounced, statusFilter, loadList]);

  const ranged = useMemo(
    () => items.filter((m) => inRange(m.created_at, dateRange)),
    [items, dateRange]
  );
  const pageCount = Math.max(1, Math.ceil(ranged.length / PAGE));
  const safePage = Math.min(page, pageCount - 1);
  const shown = ranged.slice(safePage * PAGE, safePage * PAGE + PAGE);
  const from = ranged.length === 0 ? 0 : safePage * PAGE + 1;
  const to = Math.min(ranged.length, (safePage + 1) * PAGE);

  async function refreshAfterSave() {
    await loadStats();
    await loadList({
      search: debounced,
      verified:
        statusFilter === "verified" ? true : statusFilter === "review" ? false : null,
    });
  }

  async function openDetail(id) {
    setError("");
    try {
      const ms = await getManuscript(id);
      setSelected(ms);
      setDraft(
        ms.transcription?.verified_transcription ||
          ms.transcription?.ai_transcription ||
          ""
      );
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
      setSavedNotice(true);
      await refreshAfterSave();
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
        <div className="lib-detail-head">
          <div>
            <button type="button" className="lib-back" onClick={() => setSelected(null)}>
              <IconArrowLeft style={{ width: 13, height: 13 }} />
              Back to library
            </button>
            <h1 className="page-title">
              {selected.title}
              <small className="detail-id">#{selected.id}</small>
              {tr?.verified_transcription ? (
                <span className="status-badge green-wrap">
                  <i className="dot green" />
                  Verified
                </span>
              ) : (
                <span className="status-badge amber-wrap">
                  <i className="dot amber" />
                  Needs review
                </span>
              )}
            </h1>
            {selected.notes && <p className="lede">{selected.notes}</p>}
          </div>
        </div>

        <div className="analysis">
          <CompareSlider
            original={imgUrl(selected.original_image_url)}
            restored={imgUrl(selected.restored_image_url)}
            leftLabel="Original"
            rightLabel="Restored"
          />
          <div className="analysis-side">
            <TextPanel
              title="AI transcription draft"
              value={tr?.ai_transcription}
              badge={
                <span className="badge warn">
                  <IconLock style={{ width: 11, height: 11 }} />
                  Immutable
                </span>
              }
            />
            {/* No `latin`: the verified text is Devanagari, exactly like the
                draft above and the editing textarea below it. Forcing the sans
                stack here rendered the two views of the same string in
                different faces. */}
            <TextPanel
              title="Verified transcription (human-edited)"
              value={editing ? undefined : tr?.verified_transcription}
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
                      {saving ? "Saving…" : "Save verified text"}
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
                  <span className="xs faint">Saved separately from the AI draft.</span>
                </div>
              )}
            </TextPanel>
          </div>
        </div>

        {savedNotice && (
          <p className="notice ok" role="status">
            Verification saved. The original AI draft is preserved.
          </p>
        )}
        {error && (
          <p className="notice err" role="alert">
            {error}
          </p>
        )}
      </>
    );
  }

  const filterActive = Boolean(debounced) || statusFilter !== "all" || dateRange !== "all";

  return (
    <>
      <div className="library-top">
        <div className="library-left">
          <span className="lib-dash" aria-hidden="true" />
          <h1 className="page-title">Manuscript library</h1>
          <p className="lede">Search archived records and continue human verification.</p>

          <div className="lib-search">
            <IconSearch style={{ width: 16, height: 16 }} />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search verified or AI text…"
              aria-label="Search the library"
            />
          </div>

          <div className="lib-filters">
            <select
              className={statusFilter === "all" ? "fselect dark" : "fselect"}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              aria-label="Status filter"
            >
              <option value="all">All records</option>
              <option value="review">Needs review</option>
              <option value="verified">Verified</option>
            </select>

            <select
              className="fselect"
              value={dateRange}
              onChange={(e) => {
                setDateRange(e.target.value);
                setPage(0);
              }}
              aria-label="Date range"
              title="Filter by the date a record was added"
            >
              {DATE_RANGES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>

            <div className="viewtoggle" role="group" aria-label="Layout">
              <button
                type="button"
                className={view === "grid" ? "on" : ""}
                onClick={() => setView("grid")}
                aria-pressed={view === "grid"}
                title="Grid view"
              >
                <IconGrid style={{ width: 14, height: 14 }} />
                Grid
              </button>
              <button
                type="button"
                className={view === "list" ? "on" : ""}
                onClick={() => setView("list")}
                aria-pressed={view === "list"}
                title="List view"
              >
                <IconList style={{ width: 14, height: 14 }} />
                List
              </button>
            </div>
          </div>
        </div>

        <aside className="glance" aria-label="Archive at a glance">
          <div className="glance-head">
            <span className="glance-icon">
              <IconBook style={{ width: 17, height: 17 }} />
            </span>
            <span className="glance-title">Archive at a glance</span>
          </div>
          <div className="glance-stats">
            <div>
              <span className="glance-label">Records</span>
              <b>{stats.total}</b>
            </div>
            <div>
              <span className="glance-label">
                <i className="dot amber" /> Needs review
              </span>
              <b>{stats.review}</b>
            </div>
            <div>
              <span className="glance-label">
                <i className="dot green" /> Verified
              </span>
              <b>{stats.verified}</b>
            </div>
          </div>
          <p className="glance-tagline">
            Preserving historical records through AI and human insight.
          </p>
        </aside>
      </div>

      {error && (
        <p className="notice err" role="alert">
          {error}
        </p>
      )}

      {view === "list" ? (
        <section className="lib-panel">
          <div className="lib-table-head" aria-hidden="true">
            <span>Record</span>
            <span>Added</span>
            <span>Status</span>
            <span>Transcript</span>
            <span>Actions</span>
          </div>

          {shown.map((m) => {
            const stamp = splitStamp(m.created_at);
            return (
              <article key={m.id} className="lib-row" onClick={() => openDetail(m.id)}>
                <div
                  className="lr-record"
                  role="link"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      openDetail(m.id);
                    }
                  }}
                  aria-label={`Open ${m.title}`}
                >
                  {m.thumbnail_url ? (
                    <img src={imgUrl(m.thumbnail_url)} alt="" loading="lazy" />
                  ) : (
                    <span className="lr-thumb-empty" aria-hidden="true" />
                  )}
                  <div className="lr-copy">
                    <h3>
                      {m.title}
                      {m.identifier && <span className="detail-id"> · {m.identifier}</span>}
                    </h3>
                    {m.notes && <p>{m.notes}</p>}
                  </div>
                </div>
                <div className="lr-added">
                  <b>{stamp.date}</b>
                  {stamp.time && <span>{stamp.time}</span>}
                </div>
                <div>
                  <span
                    className={m.verified ? "status-badge green-wrap" : "status-badge amber-wrap"}
                  >
                    <i className={m.verified ? "dot green" : "dot amber"} />
                    {m.verified ? "Verified" : "Needs review"}
                  </span>
                </div>
                <div>
                  <span className={m.verified ? "t-pill human" : "t-pill ai"}>
                    {m.verified ? "Human verified" : "AI draft"}
                  </span>
                </div>
                <div className="lr-actions">
                  <button
                    type="button"
                    className="btn ghost sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      openDetail(m.id);
                    }}
                  >
                    <IconEye style={{ width: 13, height: 13, marginRight: 5 }} />
                    View
                  </button>
                  <button
                    type="button"
                    className="btn ghost sm lr-more"
                    onClick={(e) => {
                      e.stopPropagation();
                      openDetail(m.id);
                    }}
                    aria-label={`Open ${m.title}`}
                    title="Open record"
                  >
                    <IconDots style={{ width: 14, height: 14 }} />
                  </button>
                </div>
              </article>
            );
          })}

          {shown.length === 0 && !loading && !error && (
            <div className="lib-empty">
              <p>
                No records{filterActive ? " match these filters" : " yet"}.
              </p>
              {onNavigateTranscribe && (
                <button type="button" className="btn" onClick={onNavigateTranscribe}>
                  Transcribe a manuscript
                </button>
              )}
            </div>
          )}

          {loading && (
            <p className="muted" role="status" style={{ padding: "14px 18px" }}>
              <span className="spinner" /> Loading records…
            </p>
          )}

          <div className="lib-foot">
            <p className="muted" style={{ margin: 0 }}>
              Showing {from}–{to} of {ranged.length} record{ranged.length === 1 ? "" : "s"}
            </p>
            <div className="pager" aria-label="Pagination">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={safePage === 0}
                aria-label="Previous page"
              >
                ‹
              </button>
              <button type="button" className="page-num on" disabled>
                {safePage + 1}
              </button>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                disabled={safePage >= pageCount - 1}
                aria-label="Next page"
              >
                ›
              </button>
            </div>
          </div>
        </section>
      ) : (
        <>
          <div className="grid-cards">
            {shown.map((m) => (
              <button
                key={m.id}
                type="button"
                className="mscard"
                onClick={() => openDetail(m.id)}
              >
                {m.thumbnail_url && <img src={imgUrl(m.thumbnail_url)} alt="" loading="lazy" />}
                <span className={m.verified ? "badge ok" : "badge warn"}>
                  {m.verified ? "Verified" : "Needs review"}
                </span>
                <span className="mscard-title">{m.title}</span>
                <span className="mscard-meta">{splitStamp(m.created_at).date}</span>
              </button>
            ))}
          </div>

          {shown.length === 0 && !loading && !error && (
            <div className="lib-empty">
              <p>No records{filterActive ? " match these filters" : " yet"}.</p>
              {onNavigateTranscribe && (
                <button type="button" className="btn" onClick={onNavigateTranscribe}>
                  Transcribe a manuscript
                </button>
              )}
            </div>
          )}

          {loading && (
            <p className="muted" role="status">
              <span className="spinner" /> Loading records…
            </p>
          )}
        </>
      )}
    </>
  );
}
