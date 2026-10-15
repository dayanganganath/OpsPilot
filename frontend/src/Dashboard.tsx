import { useEffect, useState } from 'react'

type Summary = {
  total_applications: number
  total_monitors: number
  active_monitors: number
  up_monitors: number
  down_monitors: number
  error_monitors: number
  unchecked_monitors: number
  open_incidents: number
  resolved_incidents: number
}

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadSummary() {
      setLoading(true)
      setError('')

      try {
        const response = await fetch('/api/dashboard/summary/', {
          credentials: 'same-origin',
          signal: controller.signal,
        })

        if (response.status === 401 || response.status === 403) {
          throw new Error('Your session has expired. Sign in again.')
        }

        if (!response.ok) {
          throw new Error('Could not load the dashboard.')
        }

        const data: Summary = await response.json()

        if (!controller.signal.aborted) {
          setSummary(data)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Cannot connect to OpsPilot.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadSummary()

    return () => controller.abort()
  }, [reloadKey])

  const cards = summary
    ? [
        { label: 'Applications', value: summary.total_applications },
        { label: 'Total monitors', value: summary.total_monitors },
        { label: 'Active monitors', value: summary.active_monitors },
        { label: 'Services up', value: summary.up_monitors },
        { label: 'Services down', value: summary.down_monitors },
        { label: 'Check errors', value: summary.error_monitors },
        { label: 'Not checked', value: summary.unchecked_monitors },
        { label: 'Open incidents', value: summary.open_incidents },
        { label: 'Resolved incidents', value: summary.resolved_incidents },
      ]
    : []

  return (
    <section className="dashboard" aria-labelledby="dashboard-heading">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">OPERATIONS OVERVIEW</p>
          <h2 id="dashboard-heading">Service dashboard</h2>
        </div>

        <button
          type="button"
          className="refresh-button"
          disabled={loading}
          onClick={() => setReloadKey((value) => value + 1)}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {loading && <p role="status">Loading current metrics…</p>}

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && summary && (
        <>
          <div className="metrics-grid">
            {cards.map((card) => (
              <article className="metric-card" key={card.label}>
                <p>{card.label}</p>
                <strong>{card.value}</strong>
              </article>
            ))}
          </div>

          <p className="dashboard-note">
            Service status uses the latest recorded check for each active
            monitor. Select Refresh to load updated metrics.
          </p>
        </>
      )}
    </section>
  )
}
