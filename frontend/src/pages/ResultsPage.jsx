import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import TradeoffChart from '../components/TradeoffChart'
import { useConvoy } from '../state/ConvoyContext'

export default function ResultsPage() {
  const { state, runPlan } = useConvoy()
  const plan = state.plan
  const verdict = plan?.verdict
  const assignment = plan?.assignment
  const points = state.tradeoff?.points || []
  const trajs = plan?.trajectories || []

  return (
    <div className="page-scroll">
      <div className="mx-auto max-w-4xl px-5 py-10 md:py-14">
        <motion.header
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <p className="text-[0.7rem] uppercase tracking-[0.16em] text-[var(--steel-ink)] mb-2">
            Results
          </p>
          <h1 className="font-display text-4xl md:text-5xl text-[var(--ink-strong)] tracking-tight m-0">
            Opacity &amp; cost
          </h1>
          <p className="mt-3 text-[var(--ink-muted)] max-w-2xl leading-relaxed">
            Verdict from the latest plan, per-vehicle distances, and the checkpoint-density trade-off
            sweep. Run a plan on{' '}
            <Link to="/try" className="oc-text-link">
              /try
            </Link>{' '}
            if this page is empty.
          </p>
        </motion.header>

        {!plan && (
          <div className="mt-10 oc-panel oc-panel-light p-6">
            <p className="m-0 text-[var(--ink-muted)]">No plan loaded yet.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" className="oc-btn oc-btn-light active" onClick={() => runPlan('opaque')}>
                Load opaque plan
              </button>
              <Link to="/try" className="oc-btn oc-btn-light inline-flex items-center">
                Open simulation
              </Link>
            </div>
          </div>
        )}

        {plan && (
          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <section className="oc-panel oc-panel-light p-5">
              <h2 className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel-ink)] m-0 mb-3">
                Verdict
              </h2>
              <p
                className={`font-display text-3xl m-0 ${
                  verdict?.opaque ? 'text-emerald-800' : 'text-[var(--cargo)]'
                }`}
              >
                {verdict?.opaque ? 'Type-B secure' : 'Not opaque'}
              </p>
              <p className="mt-2 text-sm text-[var(--ink-muted)] leading-relaxed m-0">
                Mode: {verdict?.mode || '—'} · status: {plan.status} · iterations:{' '}
                {plan.iterations ?? '—'}
              </p>
              {verdict?.failures?.length > 0 && (
                <ul className="mt-3 text-sm text-[var(--cargo)] pl-4 m-0">
                  {verdict.failures.slice(0, 6).map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              )}
              <p className="mt-4 text-sm leading-relaxed text-[var(--ink-muted)] m-0">
                {plan.explanation}
              </p>
            </section>

            <section className="oc-panel oc-panel-light p-5">
              <h2 className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel-ink)] m-0 mb-3">
                Fleet cost
              </h2>
              {assignment ? (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm m-0">
                  <div>
                    <dt className="text-[var(--steel-ink)] text-[0.65rem] uppercase tracking-wider">
                      Total
                    </dt>
                    <dd className="font-display text-2xl m-0 mt-0.5">
                      {Number(assignment.total_cost).toFixed(0)} m
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--steel-ink)] text-[0.65rem] uppercase tracking-wider">
                      Baseline
                    </dt>
                    <dd className="font-display text-2xl m-0 mt-0.5">
                      {Number(assignment.baseline_cost).toFixed(0)} m
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--steel-ink)] text-[0.65rem] uppercase tracking-wider">
                      Extra
                    </dt>
                    <dd className="font-display text-2xl m-0 mt-0.5 text-[var(--signal)]">
                      +{Number(assignment.extra_cost).toFixed(0)} m
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--steel-ink)] text-[0.65rem] uppercase tracking-wider">
                      Overhead
                    </dt>
                    <dd className="font-display text-2xl m-0 mt-0.5">
                      {assignment.baseline_cost > 0
                        ? (
                            (100 * assignment.extra_cost) /
                            assignment.baseline_cost
                          ).toFixed(1)
                        : '0'}
                      %
                    </dd>
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-[var(--ink-muted)] m-0">No assignment data.</p>
              )}
            </section>

            <section className="oc-panel oc-panel-light p-5 md:col-span-2">
              <h2 className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel-ink)] m-0 mb-3">
                Per vehicle
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead>
                    <tr className="text-[0.65rem] uppercase tracking-wider text-[var(--steel-ink)] border-b border-[rgba(26,31,38,0.1)]">
                      <th className="py-2 font-medium">Vehicle</th>
                      <th className="py-2 font-medium">Role</th>
                      <th className="py-2 font-medium">Distance</th>
                      <th className="py-2 font-medium">Duration</th>
                      <th className="py-2 font-medium">Nodes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trajs.map((t) => (
                      <tr key={t.vehicle_id} className="border-b border-[rgba(26,31,38,0.06)]">
                        <td className="py-2.5">{t.vehicle_id}</td>
                        <td className="py-2.5 capitalize">{t.role || '—'}</td>
                        <td className="py-2.5">{Number(t.distance_m || 0).toFixed(0)} m</td>
                        <td className="py-2.5">{Number(t.duration_s || 0).toFixed(0)} s</td>
                        <td className="py-2.5">{(t.nodes || []).length}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="oc-panel oc-panel-light p-5 md:col-span-2">
              <h2 className="text-[0.7rem] uppercase tracking-[0.14em] text-[var(--steel-ink)] m-0 mb-1">
                Cost vs checkpoint density
              </h2>
              <p className="text-xs text-[var(--ink-muted)] mb-3 m-0">
                Extra fleet distance (%) as observer checkpoint coverage increases.
              </p>
              <TradeoffChart points={points} />
              {points.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr className="text-[0.65rem] uppercase tracking-wider text-[var(--steel-ink)] border-b border-[rgba(26,31,38,0.1)]">
                        <th className="py-2 font-medium">Density</th>
                        <th className="py-2 font-medium">Cameras</th>
                        <th className="py-2 font-medium">Secure</th>
                        <th className="py-2 font-medium">Overhead %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {points.map((p) => (
                        <tr
                          key={String(p.checkpoint_fraction)}
                          className="border-b border-[rgba(26,31,38,0.06)]"
                        >
                          <td className="py-2">{p.checkpoint_fraction}</td>
                          <td className="py-2">{p.n_checkpoints}</td>
                          <td className="py-2">{p.secure_found ? 'yes' : 'no'}</td>
                          <td className="py-2">
                            {p.overhead_pct == null ? '—' : Number(p.overhead_pct).toFixed(1)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
