export default function ScenarioPicker({ scenarios, selected, onChange, disabled }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel-ink)]">
        Scenario
      </span>
      <select
        className="bg-transparent border border-[rgba(26,31,38,0.2)] px-2 py-1.5 text-sm text-[var(--ink-strong)] outline-none focus:border-[var(--signal)]"
        value={selected || ''}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {(scenarios || []).map((s) => (
          <option key={s.id} value={s.id}>
            {s.name || s.id}
          </option>
        ))}
      </select>
    </label>
  )
}
