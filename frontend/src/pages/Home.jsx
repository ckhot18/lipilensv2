import { useState } from "react";
import Dropzone from "../components/Dropzone.jsx";
import HowItWorks from "../components/HowItWorks.jsx";
import SampleStrip from "../components/SampleStrip.jsx";

const SAMPLES = [
  { id: "DIRTY", file: "DIRTY.png", label: "Dirty demo", note: "low contrast" },
  { id: "CAPTURE-001", file: "CAPTURE-001.jpg", label: "Aged capture", note: "warm cast, stains" },
  { id: "CAPTURE-002", file: "CAPTURE-002.jpg", label: "Poor capture", note: "severe fade, skew" },
  { id: "CAPTURE-003", file: "CAPTURE-003.jpg", label: "Uneven light", note: "vignette, grain" },
  { id: "MT-002", file: "MT-002.png", label: "Modi script", note: "clean scan" },
  { id: "MT-048", file: "MT-048.png", label: "Short line", note: "clean scan" },
];

export default function Home({ onStart }) {
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

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

  return (
    <>
      <section className="hero">
        <div>
          <p className="kicker">Preserving the past. Digitizing it.</p>
          <h2 className="display">
            Turn handwritten
            <br />
            history into
            <br />
            searchable text.
          </h2>
          <p className="lede">
            Upload a handwritten or historical document. LipiLens cleans the image,
            recognizes the script, digitizes the text, and translates it into a
            readable language.
          </p>
        </div>

        <div>
          <Dropzone onFile={onStart} />
          {busyId && (
            <p className="notice info" role="status">
              <span className="spinner" />
              Loading sample {busyId}…
            </p>
          )}
          {error && (
            <p className="notice err" role="alert">
              {error}
            </p>
          )}
        </div>
      </section>

      <HowItWorks />

      <SampleStrip samples={SAMPLES} onPick={useSample} busyId={busyId} />
    </>
  );
}