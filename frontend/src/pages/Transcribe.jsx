import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import CompareSlider from "../components/CompareSlider.jsx";
import Dropzone from "../components/Dropzone.jsx";
import PipelineSelect from "../components/PipelineSelect.jsx";
import ProgressPanel from "../components/ProgressPanel.jsx";
import TextPanel from "../components/TextPanel.jsx";
import {
  IconArchive,
  IconArrowRight,
  IconCheck,
  IconCompare,
  IconDownload,
  IconInfo,
  IconLock,
  IconSave,
  IconWand,
  IconZoom,
} from "../components/Icons.jsx";
import {
  getManuscript,
  imgUrl,
  previewRestoration,
  startTranscription,
  transcriptionProgress,
  uploadManuscript,
  verifyTranscription,
} from "../api/client";

const PROCESSING_FLOOR_MS = 1600;

/** How often to ask the backend how far the read has got. */
const POLL_MS = 1000;

/** The three pipelines the reference design exposes as radio cards; the full
 * set stays reachable through the select underneath. */
const QUICK_CONFIGS = [
  { name: "original", label: "Original", note: "recommended" },
  { name: "enhanced", label: "Enhanced" },
  { name: "deskewed", label: "Deskew" },
];

export default function Transcribe({
  autoFile,
  onAutoFileConsumed,
  onOpenLibrary,
}) {
  const [file, setFile] = useState(autoFile ?? null);
  // `original` deliberately: the model was validated on untouched pages, and
  // every stronger restoration config measured worse (mean CER 0.316 original
  // vs 0.328 enhanced vs 0.359 full_restoration). Denoising and CLAHE erase
  // the thin Modi matras whose deletion is already the model's main error.
  const [configName, setConfigName] = useState("original");
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(Boolean(autoFile));
  const [previewMs, setPreviewMs] = useState(null);
  const [phase, setPhase] = useState("idle");
  const [title, setTitle] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState(null);
  const [draft, setDraft] = useState("");
  const [verified, setVerified] = useState(false);
  const [readMs, setReadMs] = useState(null);
  const [settled, setSettled] = useState(true);
  const [progress, setProgress] = useState(null);
  const [zoomActual, setZoomActual] = useState(false);
  const [compareOn, setCompareOn] = useState(true);

  const reading = phase === "reading";

  // Re-entrancy latch, so a second click in the same tick cannot start a
  // second run. `busy` state alone is not enough here: `read` is a useCallback
  // that cannot see a fresh `busy` before the re-render.
  //
  // It must start false — unconditionally. Seeding it from `autoFile` (as this
  // once did) wedged every run started from the Home page: the button still
  // looked enabled, but `read` bailed on its first line forever, so no request
  // was ever sent. Nothing else clears it until a file is chosen here, which
  // is why it presented as "nothing happens, no error".
  const busyRef = useRef(false);
  const settleTimer = useRef(null);
  const initialPipeline = useRef(configName);
  const [dropKey, setDropKey] = useState(0);
  const previewSeq = useRef(0);
  const pollRef = useRef(null);
  const stopPollingRef = useRef(null);

  // Local object URL for the picked scan, so the comparison has a left half
  // the instant a file exists rather than after the preview round-trip.
  // Created in the handler that accepts the file and revoked when it is
  // replaced or the view is reset, so repeated drops cannot leak.
  const localUrlRef = useRef(null);
  const [localScanUrl, setLocalScanUrl] = useState(null);

  const adoptScan = useCallback((next) => {
    if (localUrlRef.current) URL.revokeObjectURL(localUrlRef.current);
    localUrlRef.current = next ? URL.createObjectURL(next) : null;
    setLocalScanUrl(localUrlRef.current);
  }, []);

  const releaseScan = useCallback(() => adoptScan(null), [adoptScan]);

  useEffect(() => releaseScan, [releaseScan]);

  useEffect(() => () => clearTimeout(settleTimer.current), []);

  /** Stop watching a run; safe to call when nothing is being watched. */
  const stopPolling = useCallback(() => {
    clearTimeout(pollRef.current);
    pollRef.current = null;
    if (stopPollingRef.current) {
      stopPollingRef.current();
      stopPollingRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  useEffect(() => {
    if (!reading) stopPolling();
  }, [reading, stopPolling]);

  const runPreview = useCallback(
    async (source, pipeline) => {
      if (!source) return;
      const seq = ++previewSeq.current;
      setPreviewing(true);
      try {
        const res = await previewRestoration(source, pipeline);
        if (seq !== previewSeq.current) return;
        setPreview({
          original: imgUrl(res.original_url),
          restored: imgUrl(res.restored_url),
          config: res.config_name,
        });
        setPreviewMs(res.elapsed_ms);
        setError("");
      } catch (err) {
        if (seq !== previewSeq.current) return;
        setError(`Restoration preview failed: ${err.message}`);
        setPreview(null);
      } finally {
        if (seq === previewSeq.current) setPreviewing(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    clearTimeout(settleTimer.current);
    previewSeq.current += 1;
    busyRef.current = false;
    setBusy(false);
    setDropKey((n) => n + 1);
    setFile(null);
    releaseScan();
    setPreview(null);
    setPreviewing(false);
    setPreviewMs(null);
    setResult(null);
    setDraft("");
    setVerified(false);
    setPhase("idle");
    setError("");
    setNotice("");
    setReadMs(null);
    setSettled(true);
    setTitle("");
    setIdentifier("");
    setProgress(null);
    setZoomActual(false);
    setCompareOn(true);
  }, [releaseScan]);

  const beginRun = useCallback(() => {
    // Deliberately does NOT touch `busy`/`busyRef`: `read` owns both, so the
    // button state and the re-entrancy latch can never drift apart.
    setError("");
    setNotice("");
    setPhase("cleaning");
    setResult(null);
    setVerified(false);
    setSettled(false);
    setReadMs(null);
    setProgress(null);
  }, []);

  /**
   * Follow a running transcription until it reports done.
   *
   * Resolves once the archive row exists, so callers can treat it like the
   * old blocking call. Rejects only if the job itself failed — a dropped poll
   * is retried, because a hiccup on the progress endpoint must not lose a
   * five-minute run that is still going on the server. Polling stops if the
   * user navigates away, but the server keeps reading either way.
   */
  const watchTranscription = useCallback(
    (manuscriptId, startedAt) =>
      new Promise((resolve, reject) => {
        let polls = 0;
        let live = true;
        const tick = async () => {
          try {
            const p = await transcriptionProgress(manuscriptId);
            if (!live) return;
            polls += 1;
            setProgress(p);

            if (p.state === "failed") {
              reject(new Error(p.error || "Transcription failed"));
              return;
            }
            if (p.done) {
              // The worker commits the row just before flagging done.
              const full = await getManuscript(manuscriptId);
              setResult(full);
              setDraft(
                full.transcription?.verified_transcription ||
                  full.transcription?.ai_transcription ||
                  ""
              );
              setReadMs(performance.now() - startedAt);
              setPhase("done");
              resolve(full);
              return;
            }
            pollRef.current = setTimeout(tick, POLL_MS);
          } catch (err) {
            if (!live) return;
            // Tolerate a few bad polls before giving up: the run continues
            // server-side regardless of what the browser can see.
            if (polls > 5) {
              reject(err);
              return;
            }
            pollRef.current = setTimeout(tick, POLL_MS * 2);
          }
        };
        tick();
        // Released on unmount so an in-flight poll cannot resurrect the loop.
        stopPollingRef.current = () => {
          live = false;
        };
      }),
    []
  );

  const read = useCallback(
    async (source, pipeline) => {
      if (!source) {
        // Nothing to read: never strand the UI on "cleaning".
        setPhase("idle");
        setSettled(true);
        return;
      }
      if (busyRef.current) return;
      busyRef.current = true;
      // `read` owns `busy` for its whole lifetime, so the flag and the latch
      // can never disagree about whether a run is in flight.
      setBusy(true);
      const started = performance.now();

      let ms;
      try {
        ms = await uploadManuscript(source, {
          title,
          identifier,
          configName: pipeline,
          transcribe: false,
        });
        setResult(ms);
        if (ms.duplicate) {
          setNotice(
            "Identical image and pipeline already archived — showing the existing record."
          );
        }
      } catch (err) {
        setError(err.message);
        setPhase("failed");
        setBusy(false);
        busyRef.current = false;
        setSettled(true);
        return;
      }

      settleTimer.current = setTimeout(() => setSettled(true), PROCESSING_FLOOR_MS);

      if (ms.transcription) {
        setDraft(
          ms.transcription.verified_transcription ||
            ms.transcription.ai_transcription ||
            ""
        );
        setReadMs(performance.now() - started);
        setBusy(false);
        busyRef.current = false;
        setPhase("done");
        return;
      }

      setPhase("reading");
      setProgress(null);
      try {
        // The model reads in the background; this only starts the job. From
        // here the UI follows GET /progress instead of blocking on a request
        // that stays open for minutes.
        await startTranscription(ms.id);
        await watchTranscription(ms.id, started);
      } catch (err) {
        stopPolling();
        setProgress(null);
        setError(`${err.message} — the cleaned image is safe in your library.`);
        setPhase("cleaned");
      } finally {
        setBusy(false);
        busyRef.current = false;
      }
    },
    [identifier, stopPolling, title, watchTranscription]
  );

  useEffect(() => {
    if (!autoFile) return;
    onAutoFileConsumed();
    // `file` is already set by the useState initialiser above: App remounts this
    // component (key={runToken}) for every file handed over from Home. This
    // effect only has to build the local preview URL.
    adoptScan(autoFile);
    const kick = setTimeout(() => runPreview(autoFile, initialPipeline.current), 0);
    return () => clearTimeout(kick);
  }, [autoFile, adoptScan, runPreview, onAutoFileConsumed]);

  function chooseFile(next) {
    if (!next) {
      reset();
      return;
    }
    reset();
    setDropKey((n) => n + 1);
    adoptScan(next);
    setFile(next);
    setPreviewing(true);
    runPreview(next, configName);
  }

  function onPipelineChange(next) {
    setConfigName(next);
    if (file) runPreview(file, next);
  }

  async function onVerify() {
    if (!result?.transcription || busyRef.current) return;
    const text = draft.trim();
    if (!text) {
      setError("Verified text must not be empty.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await verifyTranscription(result.transcription.id, text);
      setVerified(true);
      setNotice("Verification saved. The original AI draft is preserved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function onArchive() {
    // The record lives in the library from the moment of upload; archiving
    // with verified text simply hands the user to that record's home.
    if (onOpenLibrary) onOpenLibrary();
  }

  function onDownload() {
    const blob = new Blob([draft], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lipilens-${result?.id ?? "transcription"}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const tr = result?.transcription;
  const isVerified = verified || Boolean(tr?.verified_transcription);
  const archived = Boolean(result);
  // Before the preview round-trip returns there is no server-rendered original
  // yet, and gating the compare view on it swapped the whole panel for the
  // Dropzone on every drop — the scan vanished for a beat and the "click to
  // replace" affordance with it. Fall back to the file the user just picked so
  // the left half of the comparison is live the instant a scan exists.
  const originalUrl = archived
    ? imgUrl(result.original_image_url)
    : preview?.original || localScanUrl;
  const restoredUrl = archived
    ? imgUrl(result.restored_image_url)
    : preview?.restored || null;
  const streaming = reading ? progress?.partial_text || "" : "";
  const draftText = tr?.ai_transcription || "";
  const words = useMemo(() => draft.trim().split(/\s+/).filter(Boolean).length, [draft]);
  const chars = draft.length;
  const restoreMsFmt =
    previewMs == null ? null : previewMs < 1000 ? `${Math.round(previewMs)} ms` : `${(previewMs / 1000).toFixed(1)} s`;

  // Stepper: 1 image present, 2 draft exists, 3 human verified, 4 archived.
  const steps = [
    { n: 1, label: "Image", state: originalUrl ? "done" : "active" },
    {
      n: 2,
      label: "AI draft",
      state: reading ? "active" : tr ? "done" : "pending",
    },
    {
      n: 3,
      label: "Human verification",
      state: isVerified ? "done" : tr ? "active" : "pending",
    },
    {
      n: 4,
      label: "Archive",
      state: isVerified && archived ? "done" : isVerified ? "active" : "pending",
    },
  ];

  return (
    <>
      <header className="page-head">
        <p className="page-kicker">AI-assisted transcription</p>
        <h1 className="page-title">Transcribe a manuscript</h1>
        <p className="page-substeps">
          <span>Upload</span>
          <i aria-hidden="true" />
          <span>preview</span>
          <i aria-hidden="true" />
          <span>review</span>
          <i aria-hidden="true" />
          <span>archive</span>
        </p>
      </header>

      <div className="transcribe-grid">
        {/* ---- left: image + restoration ---- */}
        <section className="card panel">
          <div className="panel-image-head">
            <h2 className="panel-title">Manuscript image</h2>
            <div className="viewer-tools">
              <button
                type="button"
                className={zoomActual ? "vtool on" : "vtool"}
                onClick={() => setZoomActual((v) => !v)}
                disabled={!originalUrl}
                aria-pressed={zoomActual}
                title={zoomActual ? "Show fitted width" : "Show actual pixels"}
              >
                <IconZoom style={{ width: 13, height: 13 }} />
                {zoomActual ? "100%" : "Fit"}
              </button>
              <button
                type="button"
                className={compareOn ? "vtool on" : "vtool"}
                onClick={() => setCompareOn((v) => !v)}
                disabled={!originalUrl || !restoredUrl}
                aria-pressed={compareOn}
                title="Compare original with restored"
              >
                <IconCompare style={{ width: 13, height: 13 }} />
                Compare
              </button>
            </div>
          </div>

          <div className={zoomActual && !compareOn ? "viewer actual" : "viewer"}>
            {originalUrl ? (
              compareOn && restoredUrl ? (
                <CompareSlider
                  key={`${dropKey}-${configName}`}
                  original={originalUrl}
                  restored={restoredUrl}
                  leftLabel="Original"
                  rightLabel={archived ? configName : "Restored"}
                  processing={previewing || (!settled && archived)}
                />
              ) : (
                <figure className="viewer-single">
                  <img
                    src={originalUrl}
                    alt="Original manuscript"
                    className="cmp-img"
                  />
                  <figcaption className="tag left">
                    Original
                    {previewing && <span className="spinner" style={{ marginLeft: 6 }} />}
                  </figcaption>
                </figure>
              )
            ) : (
              <Dropzone key={dropKey} initialFile={file} onFile={chooseFile} />
            )}
          </div>

          <div className="preproc">
            <div className="preproc-head">
              <h3>Preprocessing / Restoration</h3>
              <span className="preproc-info" title="Changes can affect recognition — the original is always preserved">
                <IconInfo style={{ width: 14, height: 14 }} />
              </span>
            </div>

            <div className="preproc-cards" role="radiogroup" aria-label="Restoration pipeline">
              {QUICK_CONFIGS.map((cfg) => {
                const active = configName === cfg.name;
                const thumb =
                  active && compareOn && restoredUrl ? restoredUrl : originalUrl;
                return (
                  <label key={cfg.name} className={active ? "tp-card active" : "tp-card"}>
                    <span className="tp-thumb">
                      {thumb && <img src={thumb} alt="" loading="lazy" />}
                    </span>
                    <span className="tp-radio" aria-hidden="true" />
                    <span className="tp-label">
                      <b>{cfg.label}</b>
                      {cfg.note && <small>{`(${cfg.note})`}</small>}
                    </span>
                    <input
                      type="radio"
                      name="pipeline"
                      value={cfg.name}
                      checked={active}
                      disabled={busy || !file}
                      onChange={() => onPipelineChange(cfg.name)}
                    />
                  </label>
                );
              })}
            </div>

            <p className="preproc-note">
              Restoration is optional — changes can affect recognition.
              {restoreMsFmt && !previewing ? ` (${restoreMsFmt})` : ""}
            </p>

            <div className="preproc-actions">
              <button
                type="button"
                className="btn ghost"
                onClick={() => file && runPreview(file, configName)}
                disabled={!file || previewing || busy}
              >
                {previewing ? (
                  <>
                    <span className="spinner" style={{ marginRight: 6 }} />
                    Restoring…
                  </>
                ) : (
                  "Preview image"
                )}
              </button>
              <PipelineSelect
                value={configName}
                onChange={onPipelineChange}
                disabled={busy}
              />
            </div>

            <div className="grid2-fields ms-fields">
              <label className="field">
                Title (optional)
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Peshwa-era letter"
                />
              </label>
              <label className="field">
                Identifier (optional)
                <input
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="e.g. ACC-42"
                />
              </label>
            </div>
          </div>
        </section>

        {/* ---- right: workflow column ---- */}
        <div className="panel-side">
          <section className="card stepper" aria-label="Workflow steps">
            {steps.map((s, i) => (
              <div className="step-block" key={s.n}>
                {i > 0 && <span className="step-link" aria-hidden="true" />}
                <div className={`step-node ${s.state}`}>
                  <span className="step-node-num">
                    {s.state === "done" ? (
                      <IconCheck style={{ width: 12, height: 12 }} />
                    ) : (
                      s.n
                    )}
                  </span>
                  <span className="step-node-label">{s.label}</span>
                </div>
              </div>
            ))}
          </section>

          <section className="card">
            <div className="read-row">
              <button
                type="button"
                className="btn read-btn"
                onClick={() => {
                  beginRun();
                  read(file, configName);
                }}
                disabled={!file || busy}
              >
                <IconWand style={{ width: 15, height: 15, marginRight: 7 }} />
                {busy ? "Working…" : "Read with AI"}
              </button>
              <div className="read-note">
                <p>
                  The AI output is a draft, not an authoritative transcription.
                </p>
                <p>Human verification is required before archiving.</p>
              </div>
            </div>

            {reading && progress && <ProgressPanel progress={progress} />}
            {!reading && progress === null && archived && (
              <p className="xs faint" style={{ margin: 0 }}>
                Restoration above needs no GPU. Only this button waits on the
                model — a one-time load, then roughly 15-60 s for a whole page.
              </p>
            )}
          </section>

          <section className="card draft-card">
            <div className="textcard-head">
              <h3 className="textcard-title">AI transcription draft</h3>
              <span className="badge warn">
                <IconLock style={{ width: 11, height: 11 }} />
                Needs human review
              </span>
              <span className="readonly-lock">
                <IconLock style={{ width: 12, height: 12 }} />
                Read only
              </span>
            </div>

            <div className="draftbox">
              <p className="textcard-body deva">
                {reading
                  ? streaming || <span className="skeleton-lines"><span /><span /><span /></span>
                  : draftText || "—"}
              </p>
            </div>

            {tr && (
              <p className="xs faint" style={{ margin: 0 }}>
                {tr.model_name}
                {tr.inference_mode ? ` · ${tr.inference_mode}` : ""}
                {readMs ? ` · read ${(readMs / 1000).toFixed(1)}s` : ""}
                {isVerified ? " · kept immutable after verification" : ""}
              </p>
            )}
            {!tr && !reading && (
              <p className="xs faint" style={{ margin: 0 }}>
                Upload a manuscript and press “Read with AI” to generate the
                draft here.
              </p>
            )}
          </section>

          <section className="card verify-card">
            <div className="textcard-head">
              <h3 className="textcard-title">
                Verified transcription
                <span className="verify-sub">(human-edited)</span>
              </h3>
              <span className="verify-counts">
                Words: <b>{archived ? words : "—"}</b>
                <span className="count-sep">|</span>
                Characters: <b>{archived ? chars : "—"}
                </b>
              </span>
            </div>

            <textarea
              className="textarea"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={6}
              placeholder={tr ? "" : "Run the AI read first, then correct its draft here."}
              aria-label="Verified transcription"
            />

            <p className="verify-note">
              <IconInfo style={{ width: 13, height: 13, flex: "0 0 auto" }} />
              Your corrections are saved separately; the AI draft remains
              unchanged.
            </p>

            <div className="verify-actions">
              <button
                type="button"
                className={isVerified ? "btn ghost" : "btn"}
                onClick={onVerify}
                disabled={!tr || busy}
                title="Save the corrected text as the verified transcription"
              >
                {isVerified ? (
                  <>
                    <IconCheck style={{ width: 14, height: 14, marginRight: 6 }} />
                    Verified
                  </>
                ) : (
                  <>
                    <IconSave style={{ width: 14, height: 14, marginRight: 6 }} />
                    Save verified text
                  </>
                )}
              </button>
              <div className="archive-block">
                <button
                  type="button"
                  className="btn ghost archive-btn"
                  onClick={onArchive}
                  disabled={!isVerified || !archived}
                  title={
                    isVerified
                      ? "Open the archived record in your library"
                      : "Complete human verification to enable archiving"
                  }
                >
                  <IconArchive style={{ width: 14, height: 14, marginRight: 6 }} />
                  {isVerified ? "Open archived record" : "Archive record"}
                </button>
                <p className="xs muted" style={{ margin: "6px 0 0", textAlign: "right" }}>
                  {isVerified
                    ? "The verified text is stored with the record."
                    : "Complete human verification to enable archiving."}
                </p>
              </div>
            </div>

            {tr && (
              <div className="btnrow" style={{ marginTop: 10 }}>
                <button
                  type="button"
                  className="toolbtn"
                  onClick={onDownload}
                  aria-label="Download verified text as .txt"
                >
                  <IconDownload style={{ width: 13, height: 13 }} />
                  Download (.txt)
                </button>
                <span className="badge accent">
                  {tr.model_name}
                  {tr.inference_mode ? ` · ${tr.inference_mode}` : ""}
                </span>
              </div>
            )}
          </section>

          {tr?.translation && (
            <TextPanel title="Translation (English)" value={tr.translation} latin />
          )}
        </div>
      </div>

      {file && (
        <div className="btnrow" style={{ marginTop: 14 }}>
          <button type="button" className="btn ghost sm" onClick={reset} disabled={busy}>
            Process another
          </button>
          {archived && onOpenLibrary && (
            <button type="button" className="btn ghost sm" onClick={onOpenLibrary}>
              Open in Library
              <IconArrowRight style={{ width: 13, height: 13, marginLeft: 6 }} />
            </button>
          )}
        </div>
      )}

      {phase === "cleaning" && (
        <p className="notice info" role="status" aria-live="polite">
          <span className="spinner" />
          Archiving the scan and its restored version — about a second.
        </p>
      )}
      {notice && (
        <p className="notice ok" role="status">
          {notice}
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
