import { PRESET_CONFIGS } from "../api/client";

const HINTS = {
  original: "Unmodified scan — the honest baseline",
  grayscale: "Single channel, contrast stretched",
  denoised: "Edge-preserving noise removal",
  enhanced: "CLAHE local contrast, sharpened",
  binarized: "Adaptive threshold to pure ink",
  deskewed: "Rotation corrected to horizontal",
  full_restoration: "Deskew, denoise, enhance, binarize",
};

export default function PipelineSelect({ value, onChange, disabled = false }) {
  return (
    <label className="field">
      Restoration pipeline
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        {PRESET_CONFIGS.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      <span className="xs muted">{HINTS[value]}</span>
    </label>
  );
}