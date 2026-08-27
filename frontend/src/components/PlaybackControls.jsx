export default function PlaybackControls({
  playing,
  onToggle,
  playTime,
  duration,
  onSeek,
  onReset,
}) {
  const pct = duration > 0 ? Math.min(100, (playTime / duration) * 100) : 0

  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="flex items-center gap-2">
        <button type="button" className="oc-btn oc-btn-light" onClick={onReset}>
          Reset
        </button>
        <button
          type="button"
          className={`oc-btn oc-btn-light ${playing ? 'active' : ''}`}
          onClick={onToggle}
        >
          {playing ? 'Pause' : 'Play'}
        </button>
        <span className="text-xs text-[var(--steel-ink)] tabular-nums ml-auto">
          {playTime.toFixed(0)}s / {duration.toFixed(0)}s
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={duration || 1}
        step={0.1}
        value={Math.min(playTime, duration || 0)}
        onChange={(e) => onSeek(Number(e.target.value))}
        className="w-full accent-[var(--signal)]"
        style={{
          background: `linear-gradient(to right, var(--signal) ${pct}%, rgba(26,31,38,0.12) ${pct}%)`,
        }}
      />
    </div>
  )
}
