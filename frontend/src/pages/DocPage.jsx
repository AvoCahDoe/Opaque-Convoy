import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function DocPage() {
  return (
    <div className="page-scroll">
      <article className="doc-page mx-auto max-w-3xl px-5 py-10 md:py-14">
        <motion.header
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <p className="text-[0.7rem] uppercase tracking-[0.16em] text-[var(--steel-ink)] mb-2">
            Documentation
          </p>
          <h1 className="font-display text-4xl md:text-5xl text-[var(--ink-strong)] tracking-tight m-0">
            Math &amp; method
          </h1>
          <p className="mt-4 text-[var(--ink-muted)] leading-relaxed text-base md:text-lg">
            Opaque Convoy plans cargo and decoy routes so a passive camera observer cannot tell
            which vehicle carries the valuable load — with a formal Type-B guarantee and a measured
            travel-cost overhead.
          </p>
          <p className="mt-3">
            <Link to="/try" className="oc-text-link">
              Open the simulation →
            </Link>
          </p>
        </motion.header>

        <section className="doc-section">
          <h2>Problem</h2>
          <p>
            Cash-in-transit fleets are visible at public checkpoints (cameras, tolls, intersections).
            The operator wants routes where an outsider who only sees vehicles at those points cannot
            uniquely identify the cargo carrier among decoys.
          </p>
        </section>

        <section className="doc-section">
          <h2>Model</h2>
          <p>
            The street network is a finite weighted transition system (WTS). Nodes are intersections;
            edge weights are travel lengths. Each agent follows a discrete path on this graph.
          </p>
          <p>
            An observation map <span className="math">H</span> maps a node to a checkpoint id if it is
            camera-covered, and to silent <span className="math">ε</span> otherwise. The intruder sees
            only non-silent symbols.
          </p>
        </section>

        <section className="doc-section">
          <h2>Type-B security</h2>
          <p>
            Following Mitsos et al. (arXiv:2605.13134), a joint path is <strong>Type-B secure</strong> if
            whenever the cargo vehicle is secret-relevant at time <span className="math">j</span> and
            emits observation <span className="math">y ≠ ε</span>, there exists another vehicle{' '}
            <span className="math">k</span> with
          </p>
          <p className="math-block">
            H<sub>k</sub>(j) = H<sub>cargo</sub>(j) = y
          </p>
          <p>
            Intuition: at every camera hit by the cargo carrier, at least one decoy produces the same
            observation — so the intruder cannot uniquely attribute the sighting.
          </p>
        </section>

        <section className="doc-section">
          <h2>Type-A (also implemented)</h2>
          <p>
            Type-A asks for an observationally equivalent <em>copy path</em> where the agent is
            non-secret at the secret timesteps. Satisfaction of Type-A for all paths implies classical
            current-state opacity. The live demo defaults to Type-B because the product claim is
            which-vehicle ambiguity.
          </p>
        </section>

        <section className="doc-section">
          <h2>Planning loop</h2>
          <ol>
            <li>
              <strong>Planner</strong> — k-shortest cargo routes; lockstep a decoy along the cargo spine
              through shared checkpoints; insert waits to align camera times.
            </li>
            <li>
              <strong>OpacityChecker</strong> — Type-B (and optionally Type-A) on the joint assignment.
              Failures become exclusion constraints; the planner retries.
            </li>
            <li>
              <strong>TrajectoryRefiner</strong> — discrete nodes → timed lat/lng polylines.
            </li>
            <li>
              <strong>Explainer</strong> — human-readable summary (optional LLM polish).
            </li>
          </ol>
          <p>
            Orchestration uses LangGraph: Planner → OpacityChecker ⇄ replan → Refiner → Explainer.
          </p>
        </section>

        <section className="doc-section">
          <h2>Cost vs opacity</h2>
          <p>
            Sweeping checkpoint density and re-planning yields extra fleet distance (%) versus the
            shortest-path baseline. Sparse cameras are cheap to satisfy; denser observers force longer
            coordinated routes or synchronized waits. See <Link to="/results" className="oc-text-link">Results</Link>.
          </p>
        </section>

        <section className="doc-section">
          <h2>Citation</h2>
          <blockquote>
            Mitsos, G., Dimarogonas, D. V., &amp; Liu, S. (2026). Security-Aware Planning and Control of
            Multi-Agent Systems with LTL Tasks. arXiv:2605.13134.
          </blockquote>
          <p>
            <a
              className="oc-text-link"
              href="https://arxiv.org/abs/2605.13134"
              target="_blank"
              rel="noreferrer"
            >
              arXiv:2605.13134
            </a>
          </p>
        </section>
      </article>
    </div>
  )
}
