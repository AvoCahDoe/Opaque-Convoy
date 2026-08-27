export default function ScenarioPicker({ scenarios, selected, onChange, disabled }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel)]">Scenario</span>
      <select
        className="bg-transparent border border-[rgba(197,208,220,0.25)] px-2 py-1.5 text-sm text-[var(--ink)] outline-none focus:border-[var(--signal)]"
        value={selected || ''}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {(scenarios || []).map((s) => (
          <option key={s.id} value={s.id} className="bg-[var(--asphalt)]">
            {s.name || s.id}
          </option>
        ))}
      </select>
    </label>
  )
}
