import {
  IconArrowRight,
  IconBarChart,
  IconBook,
  IconGithub,
  IconImage,
  IconChip,
  IconLock,
  IconUser,
} from "../components/Icons.jsx";

export default function About({ onExploreLibrary }) {
  return (
    <div className="about-container">
      {/* Intro Hero */}
      <section className="about-intro-grid">
        <div className="about-intro-copy">
          <h1 className="about-title">About LipiLens</h1>
          <p className="about-subtitle">
            Making historical Modi-script records easier to study, verify, and search.
          </p>

          <p className="about-body-text">
            Modi script was the administrative script of Maharashtra from the 17th
            to mid-20th century. It was used for official records, letters, land
            deeds and government correspondence. Today, many of these manuscripts
            exist only as fragile, handwritten documents — often faded, damaged
            and difficult to read. Digitizing them carefully helps preserve this
            important part of our history and makes it accessible for future
            research.
          </p>
        </div>

        <div className="about-intro-visual">
          <div className="about-sample-card">
            <img
              src="/samples/MT-003.png"
              alt="Modi script manuscript sample"
              className="about-sample-img"
            />
            <p className="about-sample-caption">
              Modi script manuscript (sample)
            </p>
          </div>
        </div>
      </section>

      {/* The Process Section */}
      <section className="about-section">
        <div className="section-kicker-label">- THE PROCESS</div>

        <div className="process-cards-row">
          {/* Card 1: Restore */}
          <div className="process-card">
            <div className="process-card-header">
              <span className="process-card-num">01</span>
              <span className="process-card-icon">
                <IconImage style={{ width: 18, height: 18 }} />
              </span>
              <h3 className="process-card-title">Restore</h3>
            </div>
            <p className="process-card-desc">
              The manuscript image is optionally restored using OpenCV —
              denoising, binarization, deskewing and line segmentation to improve
              readability.
            </p>
            <div className="process-card-visual">
              <div className="orig-restore-pair">
                <div className="pair-item">
                  <img
                    src="/samples/MT-048.png"
                    alt="Original snippet"
                  />
                  <span>Original</span>
                </div>
                <span className="pair-arrow">→</span>
                <div className="pair-item">
                  <img
                    src="/samples/MT-048.png"
                    alt="Restored snippet"
                    className="filter-hint"
                  />
                  <span>Restored</span>
                </div>
              </div>
            </div>
          </div>

          <div className="process-flow-arrow" aria-hidden="true">
            <IconArrowRight style={{ width: 20, height: 20 }} />
          </div>

          {/* Card 2: Transcribe */}
          <div className="process-card">
            <div className="process-card-header">
              <span className="process-card-num">02</span>
              <span className="process-card-icon">
                <IconChip style={{ width: 18, height: 18 }} />
              </span>
              <h3 className="process-card-title">Transcribe</h3>
            </div>
            <p className="process-card-desc">
              A vision-language model (Qwen2.5-VL with Modi LoRA) reads the
              restored image and produces a draft transcription in Devanagari.
            </p>
            <div className="process-card-visual">
              <div className="transcribe-visual-pair">
                <div className="snippet-crop">
                  <img
                    src="/samples/MT-007.png"
                    alt="Line crop"
                  />
                </div>
                <span className="pair-arrow">→</span>
                <div className="draft-pill-result">
                  <div className="draft-pill-text deva">
                    स्वासनिधी राजमान्य राजश्री माधवराव...
                  </div>
                  <span className="draft-pill-sub">Model draft (Devanagari)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="process-flow-arrow" aria-hidden="true">
            <IconArrowRight style={{ width: 20, height: 20 }} />
          </div>

          {/* Card 3: Verify & Archive */}
          <div className="process-card">
            <div className="process-card-header">
              <span className="process-card-num">03</span>
              <span className="process-card-icon">
                <IconUser style={{ width: 18, height: 18 }} />
              </span>
              <h3 className="process-card-title">Verify &amp; archive</h3>
            </div>
            <p className="process-card-desc">
              A human reviewer checks and edits the draft. The verified text is
              stored separately from the AI output and made searchable in the
              library.
            </p>
            <div className="process-card-visual">
              <div className="verify-compare-pair">
                <div className="compare-mini-box">
                  <span className="mini-box-label">AI draft (immutable)</span>
                  <div className="mini-box-text deva">स्वासनिधी राजमान्य राजश्री माधवराव...</div>
                </div>
                <div className="compare-mini-box verified">
                  <span className="mini-box-label green">Verified (separate)</span>
                  <div className="mini-box-text deva">स्वासनिधी राजमान्य राजश्री माधवराव...</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Our Principles Section */}
      <section className="about-section">
        <div className="section-kicker-label">- OUR PRINCIPLES</div>
        <h2 className="principles-headline">
          Built to be reviewed, not blindly trusted
        </h2>

        <div className="principles-grid">
          <div className="principle-card">
            <div className="principle-icon-row">
              <span className="principle-icon">
                <IconLock style={{ width: 20, height: 20 }} />
              </span>
            </div>
            <h3 className="principle-title">AI output stays immutable</h3>
            <p className="principle-body">
              The model's draft transcription is kept unchanged. Any corrections
              are saved separately and never overwrite the original.
            </p>
          </div>

          <div className="principle-card">
            <div className="principle-icon-row">
              <span className="principle-icon">
                <IconUser style={{ width: 20, height: 20 }} />
              </span>
            </div>
            <h3 className="principle-title">Human verification is required</h3>
            <p className="principle-body">
              Nothing is presented as final without a human review. The human
              always remains in the loop.
            </p>
          </div>

          <div className="principle-card">
            <div className="principle-icon-row">
              <span className="principle-icon">
                <IconBarChart style={{ width: 20, height: 20 }} />
              </span>
            </div>
            <h3 className="principle-title">Measure every intervention</h3>
            <p className="principle-body">
              Preprocessing choices are evaluated empirically — denoising,
              binarization, upscaling and line segmentation are not assumed to
              improve accuracy.
            </p>
          </div>
        </div>
      </section>

      {/* Bottom Footer Bar */}
      <div className="about-footer-bar">
        <div className="about-disclaimer">
          <span className="disclaimer-info-icon">ⓘ</span>
          <span>LipiLens produces reviewable drafts, not authoritative historical transcriptions.</span>
        </div>

        <div className="about-footer-links">
          <a
            href="https://github.com/ckhot18/lipilensv2"
            target="_blank"
            rel="noreferrer"
            className="about-ext-link"
          >
            <IconGithub style={{ width: 15, height: 15, marginRight: 5 }} />
            View source on GitHub ↗
          </a>
          <button
            type="button"
            className="about-ext-btn"
            onClick={onExploreLibrary}
          >
            <IconBook style={{ width: 15, height: 15, marginRight: 5 }} />
            Explore the library ↗
          </button>
        </div>
      </div>
    </div>
  );
}