import { useCallback, useEffect, useRef, useState } from "react";

function pctFromClientX(clientX, rect) {
  if (!rect || !rect.width) return 0.5;
  return Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
}

export default function CompareSlider({
  original,
  restored,
  leftLabel = "Original",
  rightLabel = "Cleaned",
  processing = false,
}) {
  const boxRef = useRef(null);
  const activeRef = useRef(false);
  const [pos, setPos] = useState(0.5);

  const moveTo = useCallback((clientX) => {
    setPos(pctFromClientX(clientX, boxRef.current?.getBoundingClientRect()));
  }, []);

  useEffect(() => {
    function onKey(event) {
      if (event.key !== "Escape") return;
      activeRef.current = false;
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!original) {
    return (
      <div className="compare-empty">
        Upload a manuscript to compare the original scan against its restored
        version.
      </div>
    );
  }

  if (!restored) {
    return (
      <div className="compareslot">
        <img src={original} alt={leftLabel} />
        <span className="tag left">{leftLabel}</span>
      </div>
    );
  }

  const pct = Math.round(pos * 100);

  return (
    <div>
      <div
        className={processing ? "cmp is-processing" : "cmp"}
        ref={boxRef}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          activeRef.current = true;
          try {
            event.currentTarget.setPointerCapture(event.pointerId);
          } catch {
            /* capture unavailable: moves still land while over the image */
          }
          moveTo(event.clientX);
        }}
        onPointerMove={(event) => {
          if (activeRef.current) moveTo(event.clientX);
        }}
        onPointerUp={(event) => {
          activeRef.current = false;
          try {
            event.currentTarget.releasePointerCapture?.(event.pointerId);
          } catch {
            /* already released */
          }
        }}
        onPointerCancel={() => {
          activeRef.current = false;
        }}
      >
        <img className="cmp-img" src={restored} alt={`${rightLabel} manuscript`} />
        <img
          className="cmp-img cmp-top"
          src={original}
          alt={`${leftLabel} manuscript`}
          style={{ clipPath: `inset(0 ${100 - pct}% 0 0)` }}
        />

        <span className="tag left">{leftLabel}</span>
        <span className="tag right">{rightLabel}</span>

        <span className="cmp-divider" style={{ left: `${pct}%` }} aria-hidden="true">
          <span className="cmp-handle">&#8249;&#8250;</span>
        </span>

        {processing && (
          <span className="process-veil" aria-hidden="true">
            <span className="process-sweep" />
            <span className="process-label">
              <span className="spinner" />
              Restoring scan
            </span>
          </span>
        )}
      </div>

      <input
        className="comparerange"
        type="range"
        min="0"
        max="100"
        step="1"
        value={pct}
        onChange={(event) => setPos(Number(event.target.value) / 100)}
        style={{ "--fill": `${pct}%` }}
        aria-label={`Reveal ${rightLabel} image`}
        aria-valuetext={`${pct}% ${leftLabel}`}
      />
      <p className="compare-hint">
        Drag the image or the slider to compare. The original is always preserved.
      </p>
    </div>
  );
}