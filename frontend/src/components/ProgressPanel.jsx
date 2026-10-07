import { IconClock, IconTextScan } from "./Icons.jsx";

/**
 * Live progress for a background transcription run.
 *
 * The backend knows two fixed denominators — a cold model load and a line
 * count — so the bar is determinate once reading starts. Loading and
 * line-finding are unpredictable in duration, so those stages sweep instead of
 * claiming a percentage they cannot know.
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

  const sweeping = INDETERMINATE.has(stage);
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
        The GPU reads one line at a time; keep this tab open and the text
        appears line by line above.
      </p>
    </div>
  );
}