export default function About() {
  return (
    <>
      <p className="kicker">Research &amp; method</p>
      <h1 className="display" style={{ fontSize: 34 }}>
        About LipiLens
      </h1>

      <div className="hero" style={{ marginTop: 26 }}>
        <div className="card">
          <h2 className="h2">What it does</h2>
          <p className="lede" style={{ maxWidth: "none" }}>
            LipiLens is an <strong>AI-assisted</strong> preservation system for
            historical Modi Lipi manuscripts. It restores a photographed page
            with classical image processing and drafts a Devanagari
            transcription with a vision-language model (Qwen2.5-VL-3B plus a
            Modi-specialized LoRA adapter).
          </p>
        </div>

        <div className="card">
          <h2 className="h2">Why verification is mandatory</h2>
          <p className="lede" style={{ maxWidth: "none" }}>
            The model output is a <strong>draft, never ground truth</strong>.
            Every transcription stays visibly marked as unverified until a human
            reviews, corrects and explicitly verifies it. The original AI text is
            preserved permanently alongside the verified version, so nothing the
            model produced is ever silently rewritten.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="h2">The research question</h2>
        <p className="lede" style={{ maxWidth: "none" }}>
          The restoration pipeline exists to measure <em>whether and how</em>{" "}
          preprocessing helps or hurts vision-language transcription accuracy —
          including honest reports when it makes things worse. The pipeline
          selector exposes every configuration so the effect of each step can be
          reproduced on the same page.
        </p>
      </div>

      <div className="steps" style={{ marginTop: 16 }}>
        <span className="steps-title">Pipeline order</span>
        <div className="steps-body">
          <p className="step-desc" style={{ margin: 0 }}>
            deskew → denoise → enhance → binarize. Each manuscript records the
            exact configuration used, so a transcription can always be traced
            back to the image treatment that produced it.
          </p>
        </div>
      </div>
    </>
  );
}