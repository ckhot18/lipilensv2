import { useState } from "react";
import {
  IconArrowRight,
  IconCopy,
  IconEdit,
  IconImage,
  IconChip,
  IconShieldCheck,
  IconUser,
} from "../components/Icons.jsx";
import SampleStrip from "../components/SampleStrip.jsx";

const SAMPLES = [
  { id: "MT-002", file: "MT-002.png", label: "Revenue register", note: "Peshwa era, clean scan" },
  { id: "MT-003", file: "MT-003.png", label: "Admin letter", note: "Official correspondence" },
  { id: "MT-007", file: "MT-007.png", label: "Land record", note: "Village tax details" },
  { id: "MT-014", file: "MT-014.png", label: "Dispute record", note: "Boundary arbitration" },
  { id: "DIRTY", file: "DIRTY.png", label: "Dirty demo", note: "Low contrast scan" },
  { id: "MT-048", file: "MT-048.png", label: "Short order", note: "Succinct directive" },
];

export default function Home({ onStart, onNavigateTranscribe, onNavigateLibrary }) {
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("draft");

  const sampleDraftText =
    "स्वासनिधी राजमान्य राजश्री माधवराव पेशवे यांचे आज्ञेने गाव कारभार करण्यास दिला. त्यानुसार सर्व महसूल वसूल करून खजिन्यात जमा करावा. कायदयाने व प्रामाणिकपणे काम करावे.";

  async function useSample(sample) {
    setBusyId(sample.id);
    setError("");
    try {
      const res = await fetch(`/samples/${sample.file}`);
      if (!res.ok) throw new Error("Sample image is unavailable.");
      const blob = await res.blob();
      onStart(
        new File([blob], `${sample.id}.${sample.file.split(".").pop()}`, {
          type: blob.type || "image/png",
        })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  function copyDraft() {
    navigator.clipboard.writeText(sampleDraftText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="home-container">
      {/* Hero Section */}
      <section className="hero-landing">
        <div className="hero-copy-col">
          <div className="hero-kicker-row">
            <span className="hero-kicker">PRESERVING MODI MANUSCRIPTS</span>
            <span className="hero-kicker-line" aria-hidden="true" />
          </div>

          <h1 className="hero-headline">
            Give old scripts<br />
            a future.
          </h1>

          <p className="hero-lede">
            Turn historical Modi-script pages into searchable,
            human-verified Devanagari records.
          </p>

          <div className="hero-cta-row">
            <button
              type="button"
              className="btn-primary-forest"
              onClick={onNavigateTranscribe}
            >
              Transcribe a manuscript
            </button>
            <button
              type="button"
              className="btn-secondary-parchment"
              onClick={onNavigateLibrary}
            >
              Explore the library
            </button>
          </div>
        </div>

        {/* Hero Visual Column */}
        <div className="hero-visual-col">
          <div className="hero-stage">
            <figure className="hero-panel hero-panel-orig">
              <figcaption className="hero-panel-head">
                <span className="hero-panel-tag">01 · Photograph</span>
                <span className="hero-panel-note">capture-001.jpg · archive record</span>
              </figcaption>
              <img
                src="/samples/CAPTURE-001.jpg"
                alt="Historical Modi-script manuscript photographed in an archive"
                className="hero-panel-img"
              />
            </figure>

            <figure className="hero-panel hero-panel-restored">
              <figcaption className="hero-panel-head">
                <span className="hero-panel-tag is-forest">02 · Restored</span>
                <span className="hero-panel-note">OpenCV · denoise + deskew</span>
              </figcaption>
              <img
                src="/samples/MT-048.png"
                alt="A Modi-script record after OpenCV restoration"
                className="hero-panel-img"
              />
            </figure>

            {/* Overlapping Floating AI Draft Card */}
            <div className="hero-float-card">
              <div className="float-card-header">
                <span className="badge-warning-amber">
                  <span className="badge-warning-icon">▲</span> AI draft · Needs review
                </span>
              </div>

              <div className="float-card-tabs">
                <button
                  type="button"
                  className={activeTab === "draft" ? "float-tab active" : "float-tab"}
                  onClick={() => setActiveTab("draft")}
                >
                  Devanagari (AI draft)
                </button>
                <button
                  type="button"
                  className={activeTab === "verified" ? "float-tab active" : "float-tab"}
                  onClick={() => setActiveTab("verified")}
                >
                  Verified (human)
                </button>
              </div>

              <div className="float-card-body">
                <p className="float-card-text deva">
                  {sampleDraftText}
                </p>
              </div>

              <div className="float-card-footer">
                <div className="float-card-progress">
                  <span className="float-progress-label">Line 1 / 5</span>
                  <div className="float-progress-bar">
                    <div className="float-progress-fill" style={{ width: "35%" }} />
                  </div>
                </div>
                <div className="float-card-actions">
                  <button
                    type="button"
                    className="float-action-btn"
                    onClick={copyDraft}
                    title="Copy text"
                  >
                    <IconCopy style={{ width: 14, height: 14 }} />
                    {copied && <span className="copy-hint">Copied!</span>}
                  </button>
                  <button
                    type="button"
                    className="float-action-btn"
                    onClick={onNavigateTranscribe}
                    title="Edit in Transcribe"
                  >
                    <IconEdit style={{ width: 14, height: 14 }} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <p className="hero-manuscript-caption">
            PHOTOGRAPH → RESTORED SCAN → AI DRAFT → HUMAN VERIFIED
          </p>
        </div>
      </section>

      {/* The 3-Step Process Strip */}
      <section className="process-strip-section">
        <div className="process-strip-grid">
          <div className="process-strip-step">
            <div className="process-step-badge">
              <span className="step-num">01</span>
              <div className="process-icon-circle">
                <IconImage style={{ width: 18, height: 18 }} />
              </div>
            </div>
            <h3 className="process-step-title">Restore</h3>
            <p className="process-step-desc">
              Clean and enhance the manuscript image using OpenCV (denoise, binarize, deskew, segment).
            </p>
          </div>

          <div className="process-strip-arrow" aria-hidden="true">
            <IconArrowRight style={{ width: 18, height: 18 }} />
          </div>

          <div className="process-strip-step">
            <div className="process-step-badge">
              <span className="step-num">02</span>
              <div className="process-icon-circle">
                <IconChip style={{ width: 18, height: 18 }} />
              </div>
            </div>
            <h3 className="process-step-title">Transcribe</h3>
            <p className="process-step-desc">
              Qwen2.5-VL + Modi LoRA reads the image and produces a Devanagari draft (immutable).
            </p>
          </div>

          <div className="process-strip-arrow" aria-hidden="true">
            <IconArrowRight style={{ width: 18, height: 18 }} />
          </div>

          <div className="process-strip-step">
            <div className="process-step-badge">
              <span className="step-num">03</span>
              <div className="process-icon-circle">
                <IconUser style={{ width: 18, height: 18 }} />
              </div>
            </div>
            <h3 className="process-step-title">Verify &amp; archive</h3>
            <p className="process-step-desc">
              A human reviews and corrects the draft. The verified text is stored and made searchable in the library.
            </p>
          </div>
        </div>

        {/* Bottom review guarantee bar */}
        <div className="process-guarantee-bar">
          <div className="guarantee-line" />
          <div className="guarantee-pill">
            <IconShieldCheck style={{ width: 15, height: 15, marginRight: 7 }} />
            <span>AI drafts are always reviewed by a human.</span>
          </div>
          <div className="guarantee-line" />
        </div>
      </section>

      {/* Quick Interactive Samples */}
      <section className="home-samples-section">
        <SampleStrip
          samples={SAMPLES}
          onPick={useSample}
          busyId={busyId}
        />
        {error && (
          <p className="notice err" role="alert" style={{ marginTop: 12 }}>
            {error}
          </p>
        )}
      </section>
    </div>
  );
}