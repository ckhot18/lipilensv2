import { useRef, useState } from "react";
import {
  PRESET_CONFIGS,
  imgUrl,
  uploadManuscript,
  verifyTranscription,
} from "../api/client";

const MAX_BYTES = 20 * 1024 * 1024;

function CompareSlider({ original, restored, restoredLabel }) {
  const [pos, setPos] = useState(50);
  if (!original) {
    return (
      <div className="compare-empty">
        The restored image will appear here after transcription.
      </div>
    );
  }
  if (!restored) {
    return (
      <div className="compare">
        <img src={original} alt="Selected manuscript" />
        <span className="tag left">Original</span>
      </div>
    );
  }
  return (
    <div className="compare">
      <img src={original} alt="Original manuscript" />
      <div className="after" style={{ clipPath: `inset(0 0 0 ${pos}%)` }}>
        <img src={restored} alt="Restored manuscript" />
      </div>
      <span className="tag left">Original</span>
      <span className="tag right">{restoredLabel}</span>
      <div className="handle" style={{ left: `${pos}%` }}>
        <div className="knob">‹ ›</div>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        aria-label="Comparison slider"
      />
    </div>
  );
}

export default function Transcribe() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [title, setTitle] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [configName, setConfigName] = useState("full_restoration");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState(null);
  const [draft, setDraft] = useState("");
  const [verified, setVerified] = useState(false);
  const fileInput = useRef(null);

  function acceptFile(f) {
    setError("");
    setNotice("");
    setResult(null);
    setVerified(false);
    if (preview) {
      URL.revokeObjectURL(preview);
      setPreview(null);
    }
    if (!f) {
      setFile(null);
      setPreview(null);
      return;
    }
    if (!f.type.startsWith("image/")) {
      setError("Please choose an image file.");
      return;
    }
    if (f.size > MAX_BYTES) {
      setError("File exceeds the 20 MB limit.");
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    setResult(null);
    setVerified(false);
    try {
      const ms = await uploadManuscript(file, { title, identifier, configName });
      setResult(ms);
      setDraft(ms.transcription?.ai_transcription || "");
      if (ms.duplicate) setNotice("Identical image + pipeline already archived — showing the existing record.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onVerify() {
    if (!result?.transcription || busy) return;
    if (!draft.trim()) {
      setError("Verified text must not be empty.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await verifyTranscription(result.transcription.id, draft.trim());
      setVerified(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(draft);
      setNotice("Copied to clipboard.");
    } catch {
      setError("Copy failed in this browser — select the text manually.");
    }
  }

  function onDownload() {
    const blob = new Blob([draft], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `lipilens-${result?.id || "transcription"}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const tr = result?.transcription;
  const isVerified = verified || result?.status === "verified";

  return (
    <section className="page">
      <h2>Transcribe Modi Script</h2>
      <p className="subtitle">
        Upload an image of a Modi document and get the transcribed text using AI.
      </p>

      <div className="grid2">
        <div className="card">
          <div
            className={dragOver ? "dropzone over" : "dropzone"}
            onClick={() => fileInput.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); acceptFile(e.dataTransfer.files?.[0]); }}
          >
            <div className="bigicon">🖼</div>
            {preview ? (
              <img src={preview} alt="Selected manuscript preview" className="preview" />
            ) : (
              <>
                <p>Drag &amp; drop an image here<br />or</p>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); fileInput.current?.click(); }}
                >
                  Choose File
                </button>
              </>
            )}
            <input
              ref={fileInput}
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => acceptFile(e.target.files?.[0])}
            />
          </div>
          <p className="muted small" style={{ textAlign: "center" }}>
            Supports: JPG, PNG, WebP, BMP, TIFF &nbsp;|&nbsp; Max size: 20 MB
          </p>
          <form onSubmit={onSubmit} className="form">
            <label>
              Title (optional)
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Peshwa-era letter" />
            </label>
            <label>
              Identifier (optional)
              <input value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="e.g. ACC-42" />
            </label>
            <label>
              Restoration pipeline
              <select value={configName} onChange={(e) => setConfigName(e.target.value)}>
                {PRESET_CONFIGS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            <button type="submit" disabled={!file || busy}>
              {busy ? "Working…" : "Restore & Transcribe"}
            </button>
          </form>
        </div>

        <div className="card">
          <CompareSlider
            original={result ? imgUrl(result.original_image_url) : preview}
            restored={result ? imgUrl(result.restored_image_url) : null}
            restoredLabel={configName}
          />
          <p className="muted small" style={{ textAlign: "center" }}>
            Drag the handle to compare original vs restored. The original is always preserved.
          </p>
        </div>
      </div>

      {busy && (
        <p className="muted" role="status">
          Restoring image and running transcription… 20–70 seconds on the Colab GPU. Please wait.
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {notice && <p className="ok-text">{notice}</p>}

      {result && (
        <div className="card">
          <div className="panelhead">
            <h3>
              Transcribed Text{" "}
              <span className={isVerified ? "badge ok" : "badge warn"}>
                {isVerified ? "Verified" : "AI draft — pending review"}
              </span>
            </h3>
            <div className="actions">
              <button className="toolbtn" onClick={onCopy} title="Copy text">⧉ Copy</button>
              <button className="toolbtn" onClick={onDownload} title="Download as .txt">⬇ Download (.txt)</button>
            </div>
          </div>
          <p className="transcript">{tr?.ai_transcription || "—"}</p>
          <label>
            <span className="small muted">Edit below, then verify — the AI draft above is never altered.</span>
            <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={5} />
          </label>
          <p className="muted small">Model: {tr?.model_name} · via {tr?.inference_mode}</p>
          <button onClick={onVerify} disabled={busy || isVerified}>
            Mark as Verified
          </button>
        </div>
      )}
    </section>
  );
}
