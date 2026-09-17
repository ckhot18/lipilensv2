export default function About() {
  return (
    <section className="page">
      <h2>About LipiLens</h2>
      <div className="card">
        <p>
          LipiLens is an <strong>AI-assisted</strong> preservation system for
          historical Modi Lipi manuscripts. It restores a photographed page
          with classical image processing and drafts a Devanagari transcription
          with a vision-language model (Qwen2.5-VL-3B + a Modi-specialized
          LoRA adapter).
        </p>
        <p>
          The model output is a <strong>draft, never ground truth</strong>.
          Every transcription stays visibly marked as an unverified AI draft
          until a human reviews, corrects, and explicitly verifies it. The
          original AI text is preserved permanently alongside the verified
          version, so nothing the model produced is ever silently rewritten.
        </p>
        <p>
          Research angle: the restoration pipeline exists to measure{" "}
          <em>whether and how</em> preprocessing helps or hurts VLM
          transcription accuracy — including honest reports when it makes
          things worse.
        </p>
      </div>
    </section>
  );
}
