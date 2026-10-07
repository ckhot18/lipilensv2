import { useCallback, useEffect, useRef, useState } from "react";
import CompareSlider from "../components/CompareSlider.jsx";
import Dropzone from "../components/Dropzone.jsx";
import PipelineSelect from "../components/PipelineSelect.jsx";
import ProgressPanel from "../components/ProgressPanel.jsx";
import StatCards from "../components/StatCards.jsx";
import TextPanel from "../components/TextPanel.jsx";
import {
  IconArrowRight,
  IconDownload,
  IconShieldCheck,
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

export default function Transcribe({
  autoFile,
  onAutoFileConsumed,
  onOpenLibrary,
}) {
  const [file, setFile] = useState(autoFile ?? null);
  const [configName, setConfigName] = useState("enhanced");
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
  }, []);

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
    const kick = setTimeout(() => runPreview(autoFile, initialPipeline.current), 0);
    return () => clearTimeout(kick);
  }, [autoFile, runPreview, onAutoFileConsumed]);

  function chooseFile(next) {
    if (!next) {
      reset();
      return;
    }
    reset();
    setDropKey((n) => n + 1);
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
  const originalUrl = archived ? imgUrl(result.original_image_url) : preview?.original;
  const restoredUrl = archived ? imgUrl(result.restored_image_url) : preview?.restored;
  // Lines read so far. The archive does not store the count, so while a run is
  // live this comes from the job and it disappears on reload — better than a
  // permanent dash, and honest about where it came from.
  const linesRead = progress?.lines_total || tr?.line_count || null;
  const streaming = reading ? progress?.partial_text || "" : "";

  return (
    <>
      <div className="analysis-head">
        <div>
          <h1 className="h1">Document Analysis</h1>
          <p className="lede" style={{ marginTop: 6 }}>
            {archived
              ? "Your scan is archived and restored. Transcription runs on the GPU."
              : "Restoration is instant and CPU-only. Switch pipelines and watch the scan change."}
          </p>
        </div>
        {archived && onOpenLibrary && (
          <button type="button" className="btn ghost sm" onClick={onOpenLibrary}>
            Open in Library
          </button>
        )}
      </div>

      <StatCards
        pipeline={archived || preview ? configName : null}
        model={tr?.model_name}
        mode={tr?.inference_mode}
        lines={linesRead}
        restoreMs={previewMs}
        readMs={readMs}
      />

      <div className="analysis">
        <div>
          {originalUrl ? (
            <CompareSlider
              original={originalUrl}
              restored={restoredUrl}
              rightLabel={archived ? configName : `${configName} preview`}
              processing={previewing || (!settled && archived)}
            />
          ) : (
            <Dropzone key={dropKey} initialFile={file} onFile={chooseFile} />
          )}

          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              beginRun();
              read(file, configName);
            }}
          >
            <PipelineSelect
              value={configName}
              onChange={onPipelineChange}
              disabled={busy}
            />
            <div className="grid2-fields">
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
            <div className="btnrow">
              <button type="submit" className="btn" disabled={!file || busy}>
                {busy
                  ? "Working…"
                  : archived
                    ? "Re-read with AI"
                    : "Read with AI"}
                {!busy && (
                  <IconArrowRight style={{ width: 14, height: 14, marginLeft: 6 }} />
                )}
              </button>
              {file && (
                <button type="button" className="btn ghost" onClick={reset} disabled={busy}>
                  Process another
                </button>
              )}
            </div>
            <p className="xs muted" style={{ margin: 0 }}>
              Restoration above needs no GPU. Only this button waits on the model —
              about 95 s to load it once, then ~25 s per text line. Progress
              and the text appear here as each line is read.
            </p>
          </form>
        </div>

        <div className="analysis-side">
          <section className="card">
            <div className="textcard-head">
              <h3>Digitized Text</h3>
              {reading ? (
                <span className="badge accent">Reading…</span>
              ) : isVerified ? (
                <span className="badge ok" style={{ marginLeft: 8 }}>
                  <IconShieldCheck style={{ width: 11, height: 11 }} />
                  Verified
                </span>
              ) : tr ? (
                <span className="badge warn" style={{ marginLeft: 8 }}>
                  AI draft
                </span>
              ) : null}
            </div>

            {reading && <ProgressPanel progress={progress} />}

            <p className="textcard-body">
              {reading
                ? streaming || "—"
                : tr?.ai_transcription || "—"}
            </p>

            {reading && !streaming && (
              <div className="skeleton-lines" style={{ marginTop: 12 }}>
                <span />
                <span />
                <span />
              </div>
            )}
          </section>

          {tr?.translation && (
            <TextPanel title="Translation (English)" value={tr.translation} latin />
          )}
        </div>
      </div>

      {tr && (
        <section className="card" style={{ marginTop: 16 }}>
          <div className="textcard-head">
            <h3>Human verification</h3>
            <button
              type="button"
              className="toolbtn"
              onClick={onDownload}
              aria-label="Download as text file"
            >
              <IconDownload style={{ width: 13, height: 13 }} />
              Download (.txt)
            </button>
          </div>

          <p className="xs muted" style={{ margin: "0 0 8px" }}>
            Edit below and verify. The AI draft above is never altered.
          </p>

          <textarea
            className="textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={6}
            aria-label="Verified transcription"
            disabled={isVerified}
          />

          <div className="btnrow" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="btn"
              onClick={onVerify}
              disabled={busy || isVerified}
            >
              <IconShieldCheck style={{ width: 14, height: 14, marginRight: 6 }} />
              {isVerified ? "Verified" : "Mark as Verified"}
            </button>
            <span className="badge accent">
              {tr.model_name}
              {tr.inference_mode ? ` · ${tr.inference_mode}` : ""}
            </span>
          </div>
        </section>
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