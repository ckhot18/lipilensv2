import { IconClock, IconTextScan } from "./Icons.jsx";

/**
 * Live progress for a background transcription run.
 *
 * Line segmentation is off by default, so a read is one whole-page call: the
 * backend reports no line count and no per-line text, which leaves no
 * denominator for a real bar. The bar therefore sweeps for every stage rather
 * than claiming a percentage it cannot know. The line-count facts below are
 * kept for the SEGMENT_LINES=1 configuration, where they are real.
 */
const INDETERMINATE = new Set(["queued", "loading_model", "model_ready",
                               "segmenting"]);

function clock(seconds) {
  if (seconds == null || !Number.isFinite(seconds)) return null;
  const total = Math.max(0, Math.round(seconds));
  if (total < 60) return `${total}s`;
  const m = Math.floor(total / 60);
  const s = total % 60;
  return s ? `${m}m ${s}s` : `${m}m`;
}

export default function ProgressPanel({ progress }) {
  if (!progress) return null;

  const {
    message,
    percent,
    stage,
    lines_total: total,
    lines_done: done,
    last_line: lastLine,
    elapsed_s: elapsed,
    eta_s: eta,
  } = progress;

  // A whole-page read is one indivisible unit: the backend reports no line
  // count, so there is no denominator to draw a real bar from. Sweep rather
  // than sit frozen on a number we would have to invent.
  const sweeping = INDETERMINATE.has(stage)
    || (stage === "reading" && !total);
  const width = sweeping ? null : Math.max(2, Math.min(100, percent));

  const facts = [];
  if (total > 0) {
    facts.push(`${done} of ${total} line${total === 1 ? "" : "s"} read`);
  }
  const elapsedText = clock(elapsed);
  if (elapsedText) facts.push(`${elapsedText} elapsed`);
  const etaText = clock(eta);
  if (etaText && !sweeping) facts.push(`~${etaText} left`);

  return (
    <div className="prog">
      <div className="prog-head">
        <span className="spinner" />
        <p className="prog-msg">{message}</p>
        {!sweeping && (
          <span className="prog-pct">{Math.round(percent)}%</span>
        )}
      </div>

      <div
        className={`prog-track${sweeping ? " sweep" : ""}`}
        role="progressbar"
        aria-label="Transcription progress"
        aria-valuenow={sweeping ? undefined : percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="prog-fill"
          style={sweeping ? undefined : { width: `${width}%` }}
        />
      </div>

      {facts.length > 0 && (
        <p className="prog-facts">
          {facts.map((fact, i) => (
            <span key={fact}>
              {i > 0 && <span className="prog-sep">·</span>}
              {fact}
            </span>
          ))}
        </p>
      )}

      {lastLine && (
        <p className="prog-last">
          <IconTextScan style={{ width: 13, height: 13, flex: "0 0 auto" }} />
          <span className="deva">{lastLine}</span>
        </p>
      )}

      <p className="prog-note">
        <IconClock style={{ width: 12, height: 12, flex: "0 0 auto" }} />
        The GPU reads the whole page in one pass, not line by line — roughly
        15-60 s once the model is loaded. Keep this tab open; the text appears
        when the read finishes.
      </p>
    </div>
  );
}