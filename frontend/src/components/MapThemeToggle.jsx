export default function MapThemeToggle({ mapDark, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel-ink)]">
        Map
      </span>
      <button
        type="button"
        className={`oc-btn oc-btn-light ${!mapDark ? 'active' : ''}`}
        onClick={() => onChange(false)}
      >
        Light
      </button>
      <button
        type="button"
        className={`oc-btn oc-btn-light ${mapDark ? 'active' : ''}`}
        onClick={() => onChange(true)}
      >
        Dark
      </button>
    </div>
  )
}
