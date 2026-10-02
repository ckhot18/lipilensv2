export default function SampleStrip({ samples, onPick, busyId }) {
  return (
    <div className="samples">
      <h2 className="h2">Try LipiLens with a sample</h2>
      <div className="samples-grid">
        {samples.map((s) => (
          <button
            key={s.id}
            type="button"
            className="sample"
            onClick={() => onPick(s)}
            disabled={busyId === s.id}
            title={`${s.label} — ${s.note}`}
          >
            <img src={`/samples/${s.file}`} alt={`Sample: ${s.label}`} loading="lazy" />
            <span className="sample-label">{s.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}