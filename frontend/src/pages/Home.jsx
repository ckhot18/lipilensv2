import { useState } from "react";
import { imgUrl, uploadManuscript } from "../api/client";

/* Real MoDeTrans pages bundled with the app (id, source file, ref chars). */
const SAMPLES = [
  { id: "MT-002", src: "10.jpg", chars: 91 },
  { id: "MT-007", src: "1003.jpg", chars: 73 },
  { id: "MT-014", src: "101.jpg", chars: 153 },
  { id: "MT-003", src: "1000.jpg", chars: 120 },
  { id: "MT-048", src: "1040.jpg", chars: 76 },
];

const FEATURES = [
  ["◈", "Image Restoration", "Remove noise, enhance faded text"],
  ["🇹", "AI Transcription", "Convert Modi Lipi to readable text"],
  ["ⓘ", "Human Verification", "Keep historians in the loop"],
  ["☁", "Open Research", "Built for a more accessible past"],
];

function SampleTester({ onOpenLibrary }) {
  const [picked, setPicked] = useState(SAMPLES[0].id);
  const [view, setView] = useState("text");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function runSample() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch(`/samples/${picked}.png`);
      if (!res.ok) throw new Error("Sample image missing.");
      const blob = await res.blob();
      const ms = await uploadManuscript(
        new File([blob], `${picked}.png`, { type: "image/png" }),
        { title: `Sample ${picked}`, configName: "enhanced" }
      );
      setResult(ms);
      setView("text");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const tr = result?.transcription;

  return (
    <div className="card">
      <div className="sampletabs">
        <span className="sampletab active">ⓘ Check Sample</span>
      </div>
      <p className="muted">
        Try with a sample manuscript to see how LipiLens works — no upload needed.
      </p>
      <div className="thumbrow">
        {SAMPLES.map((s) => (
          <button
            key={s.id}
            className={picked === s.id ? "thumb picked" : "thumb"}
            onClick={() => { setPicked(s.id); setResult(null); setError(""); }}
            title={`${s.id} (${s.src}, ${s.chars} chars expert reading)`}
          >
            <img src={`/samples/${s.id}.png`} alt={`Sample ${s.id}`} />
            <span className="small muted">{s.id}</span>
          </button>
        ))}
      </div>
      <button className="runbtn" onClick={runSample} disabled={busy}>
        {busy ? "Reading… (20–70s)" : "Run Sample  →"}
      </button>
      {error && <p className="error">{error}</p>}

      {result && (
        <div className="sampleout">
          <div className="panelhead">
            <span className="badge ok">Sample Result</span>
            <button className="toolbtn" onClick={onOpenLibrary}>
              View Full Result →
            </button>
          </div>
          <div className="viewtabs">
            {["original", "restored", "text", "side"].map((v) => (
              <button
                key={v}
                className={view === v ? "viewtab active" : "viewtab"}
                onClick={() => setView(v)}
              >
                {v === "restored" ? "Enhanced" : v === "text" ? "Transcription" : v === "side" ? "Side by Side" : "Original"}
              </button>
            ))}
          </div>
          {(view === "original" || view === "side") && (
            <img className="sampleimg" src={imgUrl(result.original_image_url)} alt="Original" />
          )}
          {(view === "restored" || view === "side") && (
            <img className="sampleimg" src={imgUrl(result.restored_image_url)} alt="Restored" />
          )}
          {(view === "text" || view === "side") && (
            <p className="transcript">{tr?.ai_transcription}</p>
          )}
          <p className="muted small">
            <span className="badge warn">AI draft — pending review</span> Verify it in the Library.
          </p>
        </div>
      )}
    </div>
  );
}

export default function Home({ go }) {
  return (
    <section className="page home">
      <p className="kicker">PRESERVE · TRANSCRIBE · DISCOVER</p>
      <div className="hero">
        <div className="herotext">
          <h2 className="display">Ancient Scripts.<br />New Possibilities.</h2>
          <p>
            LipiLens uses AI to restore, transcribe, and digitize degraded
            historical manuscripts — starting with Modi Lipi.
          </p>
          <div className="btnrow">
            <button onClick={() => go("transcribe")}>Try It Now →</button>
            <button className="ghost" onClick={() => go("library")}>Explore Library</button>
          </div>
          <p className="muted small ticks">✓ No signup required &nbsp; ✓ Try sample manuscripts &nbsp; ✓ See AI in action</p>
        </div>
        <div className="heroart">
          <img src="/hero-page.png" alt="Restored Modi manuscript page" />
          <p className="handnote">History lives again.</p>
        </div>
      </div>

      <SampleTester onOpenLibrary={() => go("library")} />

      <div className="featgrid">
        {FEATURES.map(([ico, t, d]) => (
          <div key={t} className="feat">
            <div className="featic">{ico}</div>
            <strong>{t}</strong>
            <p className="muted small">{d}</p>
          </div>
        ))}
      </div>

      <div className="statsband">
        <div className="quotebox">
          <p className="transcript">“A bridge between our heritage and the future.”</p>
        </div>
        <div className="stats">
          <div><strong>50</strong><span>Test Manuscripts</span></div>
          <div><strong>140</strong><span>Measured AI Calls</span></div>
          <div><strong>100%</strong><span>Open Source</span></div>
        </div>
      </div>
    </section>
  );
}
