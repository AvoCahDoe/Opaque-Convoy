export default function ObserverToggle({ observerMode, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel)]">View</span>
      <button
        type="button"
        className={`oc-btn ${!observerMode ? 'active' : ''}`}
        onClick={() => onChange(false)}
      >
        God
      </button>
      <button
        type="button"
        className={`oc-btn ${observerMode ? 'active' : ''}`}
        onClick={() => onChange(true)}
      >
        Observer
      </button>
    </div>
  )
}
