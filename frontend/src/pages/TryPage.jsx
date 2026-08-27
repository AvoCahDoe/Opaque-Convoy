import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import MapView from '../components/MapView'
import ObserverToggle from '../components/ObserverToggle'
import PlaybackControls from '../components/PlaybackControls'
import ScenarioPicker from '../components/ScenarioPicker'
import { useConvoy } from '../state/ConvoyContext'

export default function TryPage() {
  const { state, dispatch, duration, runPlan, checkpoints } = useConvoy()
  const verdict = state.plan?.verdict
  const assignment = state.plan?.assignment

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div className="absolute inset-0 z-0">
        <MapView
          graph={state.graph}
          trajectories={state.plan?.trajectories}
          observerMode={state.observerMode}
          playTime={state.playTime}
          checkpoints={checkpoints}
        />
      </div>

      <div className="pointer-events-none absolute top-3 left-3 right-3 z-10 md:top-4 md:left-4 md:right-auto md:max-w-md">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="pointer-events-auto"
        >
          <p className="font-display text-2xl md:text-3xl text-[var(--ink-strong)] drop-shadow-sm m-0">
            Simulation
          </p>
          <p className="mt-1 text-sm text-[var(--ink-muted)] max-w-sm leading-snug bg-[rgba(248,249,250,0.75)] backdrop-blur-sm px-2 py-1 inline-block">
            Animate cargo + decoys on OpenStreetMap. Toggle Observer to see only camera hits.
          </p>
        </motion.div>
      </div>

      <aside className="absolute bottom-0 left-0 right-0 md:right-auto md:top-24 md:bottom-4 md:left-4 z-10 p-3 md:p-0 md:w-[340px]">
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="oc-panel oc-panel-light p-4 flex flex-col gap-4"
        >
          <ScenarioPicker
            scenarios={state.scenarios}
            selected={state.scenarioId}
            onChange={(id) => dispatch({ type: 'SET', payload: { scenarioId: id } })}
            disabled={state.loading}
          />

          <ObserverToggle
            observerMode={state.observerMode}
            onChange={(v) => dispatch({ type: 'SET', payload: { observerMode: v } })}
          />

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="oc-btn oc-btn-light"
              disabled={state.loading}
              onClick={() => runPlan('opaque')}
            >
              Load opaque
            </button>
            <button
              type="button"
              className="oc-btn oc-btn-light"
              disabled={state.loading}
              onClick={() => runPlan('leaky')}
            >
              Load leaky
            </button>
            <button
              type="button"
              className="oc-btn oc-btn-light active"
              disabled={state.loading}
              onClick={() => runPlan(null)}
            >
              Plan
            </button>
          </div>

          <PlaybackControls
            playing={state.playing}
            playTime={state.playTime}
            duration={duration}
            onToggle={() =>
              dispatch({ type: 'SET', payload: { playing: !state.playing } })
            }
            onSeek={(t) => dispatch({ type: 'SET', payload: { playTime: t, playing: false } })}
            onReset={() => dispatch({ type: 'SET', payload: { playTime: 0, playing: false } })}
          />

          <AnimatePresence>
            {state.plan && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0 }}
                className="text-xs leading-relaxed text-[var(--ink-muted)] border-t border-[rgba(26,31,38,0.1)] pt-3"
              >
                <p className="mb-1">
                  <span
                    className={`uppercase tracking-wider text-[0.65rem] ${
                      verdict?.opaque ? 'text-emerald-700' : 'text-[var(--cargo)]'
                    }`}
                  >
                    {verdict?.opaque ? 'Type-B secure' : 'Not opaque'}
                  </span>
                  {assignment && (
                    <span>
                      {' '}
                      · +{Number(assignment.extra_cost || 0).toFixed(0)} m vs shortest
                    </span>
                  )}
                </p>
                <p className="m-0">{state.plan.explanation}</p>
                <Link to="/results" className="oc-text-link mt-2 inline-block">
                  View results →
                </Link>
              </motion.div>
            )}
          </AnimatePresence>

          {state.error && <p className="text-xs text-[var(--cargo)] m-0">{state.error}</p>}
        </motion.div>
      </aside>

      {state.loading && (
        <div className="absolute top-4 right-4 z-20 text-xs uppercase tracking-widest text-[var(--signal)] bg-[rgba(248,249,250,0.9)] px-2 py-1">
          Computing…
        </div>
      )}
    </div>
  )
}
