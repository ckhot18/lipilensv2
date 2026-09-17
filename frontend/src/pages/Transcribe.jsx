import { useState } from "react";
import {
  PRESET_CONFIGS,
  imgUrl,
  uploadManuscript,
  verifyTranscription,
} from "../api/client";

export default function Transcribe() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [title, setTitle] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [configName, setConfigName] = useState("full_restoration");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [draft, setDraft] = useState("");
  const [verified, setVerified] = useState(false);

  function onFile(e) {
    const f = e.target.files?.[0];
    setError("");
    setResult(null);
    setVerified(false);
    if (!f) {
      setFile(null);
      setPreview(null);
      return;
    }
    if (!f.type.startsWith("image/")) {
      setError("Please choose an image file.");
      return;
    }
    if (f.size > 20 * 1024 * 1024) {
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
    setResult(null);
    setVerified(false);
    try {
      const ms = await uploadManuscript(file, { title, identifier, configName });
      setResult(ms);
      setDraft(ms.transcription?.ai_transcription || "");
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

  const tr = result?.transcription;

  return (
    <section className="page">
      <h2>Transcribe a manuscript</h2>
      <p className="muted">
        Upload a Modi manuscript page. The original is always preserved; the AI
        draft is <strong>never</strong> treated as ground truth.
      </p>

      <form onSubmit={onSubmit} className="card form">
        <label>
          Image
          <input type="file" accept="image/*" onChange={onFile} />
        </label>
        {preview && (
          <img src={preview} alt="Selected manuscript preview" className="preview" />
        )}
        <label>
          Title (optional)
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Peshwa-era letter"
          />
        </label>
        <label>
          Identifier (optional)
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="e.g. ACC-42"
          />
        </label>
        <label>
          Restoration pipeline
          <select value={configName} onChange={(e) => setConfigName(e.target.value)}>
            {PRESET_CONFIGS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={!file || busy}>
          {busy ? "Working…" : "Restore & Transcribe"}
        </button>
      </form>

      {busy && (
        <p className="muted" role="status">
          Restoring image and running transcription… this takes 20–70 seconds
          on the Colab GPU. Please wait.
        </p>
      )}
      {error && <p className="error">{error}</p>}

      {result && (
        <div className="card">
          <h3>
            Result #{result.id}{" "}
            <span className={verified || result.status === "verified" ? "badge ok" : "badge warn"}>
              {verified || result.status === "verified" ? "Verified" : "AI draft — pending review"}
            </span>{" "}
            {result.duplicate && <span className="badge">duplicate upload</span>}
          </h3>
          <div className="imgrow">
            <figure>
              <figcaption>Original (preserved)</figcaption>
              <img src={imgUrl(result.original_image_url)} alt="Original manuscript" />
            </figure>
            <figure>
              <figcaption>Restored ({configName})</figcaption>
              <img src={imgUrl(result.restored_image_url)} alt="Restored manuscript" />
            </figure>
          </div>
          <label>
            AI transcription — edit freely, then verify
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={6}
            />
          </label>
          <p className="muted small">
            Model: {tr?.model_name} · via {tr?.inference_mode}
          </p>
          <button onClick={onVerify} disabled={busy || verified || result.status === "verified"}>
            Mark as Verified
          </button>
          {verified && <p className="ok-text">Saved as human-verified. It now appears verified in My Library.</p>}
        </div>
      )}
    </section>
  );
}
