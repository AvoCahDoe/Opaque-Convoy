import { createContext, useContext, useEffect, useMemo, useReducer, useRef } from 'react'
import { fetchGraph, fetchScenarios, fetchTradeoff, planRoutes } from '../api'

const ConvoyContext = createContext(null)

const initial = {
  scenarios: [],
  scenarioId: 'providence_fd',
  graph: null,
  plan: null,
  tradeoff: null,
  observerMode: false,
  mapDark: true,
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

export function ConvoyProvider({ children }) {
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
          /* optional */
        }
      } catch (e) {
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

  const value = {
    state,
    dispatch,
    duration,
    runPlan,
    checkpoints: state.graph?.scenario?.checkpoints || [],
  }

  return <ConvoyContext.Provider value={value}>{children}</ConvoyContext.Provider>
}

export function useConvoy() {
  const ctx = useContext(ConvoyContext)
  if (!ctx) throw new Error('useConvoy must be used within ConvoyProvider')
  return ctx
}
