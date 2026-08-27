import { useEffect, useMemo, useReducer, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchGraph, fetchScenarios, fetchTradeoff, planRoutes } from './api'
import MapView from './components/MapView'
import ObserverToggle from './components/ObserverToggle'
import PlaybackControls from './components/PlaybackControls'
import ScenarioPicker from './components/ScenarioPicker'
import TradeoffChart from './components/TradeoffChart'

const initial = {
  scenarios: [],
  scenarioId: 'providence_fd',
  graph: null,
  plan: null,
  tradeoff: null,
  observerMode: false,
  playing: false,
  playTime: 0,
  loading: false,
  error: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET':
      return { ...state, ...action.payload }
    default:
      return state
  }
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, initial)
  const playTimeRef = useRef(0)
  const playingRef = useRef(false)
  const durationRef = useRef(0)
  const rafRef = useRef(null)
  const lastTs = useRef(null)

  const duration = useMemo(() => {
    const trajs = state.plan?.trajectories || []
    if (!trajs.length) return 0
    return Math.max(...trajs.map((t) => t.duration_s || 0), 0)
  }, [state.plan])

  useEffect(() => {
    playTimeRef.current = state.playTime
  }, [state.playTime])

  useEffect(() => {
    playingRef.current = state.playing
  }, [state.playing])

  useEffect(() => {
    durationRef.current = duration
  }, [duration])

  const checkpoints = state.graph?.scenario?.checkpoints || []

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const scenarios = await fetchScenarios()
        if (cancelled) return
        const preferred =
          scenarios.find((s) => s.id === 'providence_fd')?.id ||
          scenarios[0]?.id ||
          'toy'
        dispatch({ type: 'SET', payload: { scenarios, scenarioId: preferred } })
      } catch (e) {
        dispatch({ type: 'SET', payload: { error: String(e.message || e) } })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!state.scenarioId) return
    let cancelled = false
    ;(async () => {
      dispatch({ type: 'SET', payload: { loading: true, error: null, plan: null } })
      try {
        const [graph, tradeoff] = await Promise.all([
          fetchGraph(state.scenarioId),
          fetchTradeoff(state.scenarioId).catch(() => null),
        ])
        if (cancelled) return
        dispatch({
          type: 'SET',
          payload: { graph, tradeoff, loading: false, playTime: 0, playing: false },
        })
        // Showcase: auto-load opaque seed so the map is immediately demonstrable
        try {
          const plan = await planRoutes({
            scenario_id: state.scenarioId,
            use_seed: 'opaque',
            use_llm: false,
          })
          if (!cancelled) {
            dispatch({ type: 'SET', payload: { plan, playTime: 0, playing: false } })
          }
        } catch {
          /* planning optional on first paint */
        }      } catch (e) {
        if (!cancelled) {
          dispatch({
            type: 'SET',
            payload: { loading: false, error: String(e.message || e) },
          })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [state.scenarioId])

  useEffect(() => {
    if (!state.playing) {
      lastTs.current = null
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return undefined
    }

    const step = (ts) => {
      if (!playingRef.current) return
      if (lastTs.current == null) lastTs.current = ts
      const dt = (ts - lastTs.current) / 1000
      lastTs.current = ts
      const next = Math.min(durationRef.current, playTimeRef.current + dt * 1.5)
      playTimeRef.current = next
      dispatch({ type: 'SET', payload: { playTime: next } })
      if (next >= durationRef.current) {
        dispatch({ type: 'SET', payload: { playing: false } })
        return
      }
      rafRef.current = requestAnimationFrame(step)
    }

    rafRef.current = requestAnimationFrame(step)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      lastTs.current = null
    }
  }, [state.playing])

  async function runPlan(seed) {
    dispatch({ type: 'SET', payload: { loading: true, error: null } })
    try {
      const plan = await planRoutes({
        scenario_id: state.scenarioId,
        use_seed: seed,
        use_llm: false,
      })
      const tradeoff = await fetchTradeoff(state.scenarioId).catch(() => state.tradeoff)
      dispatch({
        type: 'SET',
        payload: {
          plan,
          tradeoff,
          loading: false,
          playTime: 0,
          playing: false,
        },
      })
    } catch (e) {
      dispatch({ type: 'SET', payload: { loading: false, error: String(e.message || e) } })
    }
  }

  const verdict = state.plan?.verdict
  const assignment = state.plan?.assignment

  return (
    <div className="relative h-full w-full">
      <div className="absolute inset-0 z-0">
        <MapView
          graph={state.graph}
          trajectories={state.plan?.trajectories}
          observerMode={state.observerMode}
          playTime={state.playTime}
          checkpoints={checkpoints}
        />
      </div>

      <header className="pointer-events-none absolute top-0 left-0 right-0 z-10 p-5 md:p-8">
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="pointer-events-auto max-w-xl"
        >
          <p className="font-display text-4xl md:text-5xl tracking-tight text-[var(--ink)]">
            Opaque Convoy
          </p>
          <p className="mt-2 text-sm md:text-base text-[var(--fog)] max-w-md leading-relaxed">
            Route a high-value carrier so a camera observer cannot tell which vehicle holds the cargo.
          </p>
        </motion.div>
      </header>

      <aside className="absolute bottom-0 left-0 right-0 md:right-auto md:top-28 md:bottom-6 md:left-6 z-10 p-4 md:p-0 md:w-[340px]">
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="oc-panel p-4 flex flex-col gap-4"
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
              className="oc-btn"
              disabled={state.loading}
              onClick={() => runPlan('opaque')}
            >
              Load opaque
            </button>
            <button
              type="button"
              className="oc-btn"
              disabled={state.loading}
              onClick={() => runPlan('leaky')}
            >
              Load leaky
            </button>
            <button
              type="button"
              className="oc-btn active"
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
                className="text-xs leading-relaxed text-[var(--fog)] border-t border-[rgba(197,208,220,0.12)] pt-3"
              >
                <p className="mb-1">
                  <span
                    className={`uppercase tracking-wider text-[0.65rem] ${
                      verdict?.opaque ? 'text-emerald-400' : 'text-[var(--cargo)]'
                    }`}
                  >
                    {verdict?.opaque ? 'Type-B secure' : 'Not opaque'}
                  </span>
                  {assignment && (
                    <span className="text-[var(--steel)]">
                      {' '}
                      · +{Number(assignment.extra_cost || 0).toFixed(0)} m vs shortest
                    </span>
                  )}
                </p>
                <p>{state.plan.explanation}</p>
              </motion.div>
            )}
          </AnimatePresence>

          {state.error && <p className="text-xs text-[var(--cargo)]">{state.error}</p>}
        </motion.div>
      </aside>

      <aside className="hidden md:block absolute bottom-6 right-6 z-10 w-[320px]">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="oc-panel p-4"
        >
          <p className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel)] mb-2">
            Cost vs opacity
          </p>
          <TradeoffChart points={state.tradeoff?.points} />
        </motion.div>
      </aside>

      {state.loading && (
        <div className="absolute top-6 right-6 z-20 text-xs uppercase tracking-widest text-[var(--signal)]">
          Computing…
        </div>
      )}
    </div>
  )
}
