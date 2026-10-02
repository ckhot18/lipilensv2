import { Fragment } from "react";
import { IconTextScan, IconTranslate, IconWand } from "./Icons.jsx";

const STEPS = [
  [IconWand, "1. Clean & Enhance", "Remove noise, fix contrast, sharpen text"],
  [IconTextScan, "2. Recognize Script", "Detect script and extract text"],
  [IconTranslate, "3. Digitize & Translate", "Convert to digital text and translate"],
];

export default function HowItWorks() {
  return (
    <div className="steps">
      <span className="steps-title">How LipiLens works?</span>
      <div className="steps-body">
        {STEPS.map(([Icon, title, desc], i) => (
          <Fragment key={title}>
            <div className="step">
              <span className="step-ic">
                <Icon />
              </span>
              <span>
                <p className="step-title">{title}</p>
                <p className="step-desc">{desc}</p>
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <span className="step-arrow" aria-hidden="true">
                &rarr;
              </span>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
}