import { useEffect, useState } from 'react'

type Incident = {
  id: number
  title: string
  monitor_name: string
  application_name: string
  status: 'open' | 'resolved'
  opened_at: string
  resolved_at: string | null
}

type StatusFilter = 'all' | 'open' | 'resolved'

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [filter, setFilter] = useState<StatusFilter>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadIncidents() {
      setLoading(true)
      setError('')

      try {
        const response = await fetch('/api/incidents/', {
          credentials: 'same-origin',
          signal: controller.signal,
        })

        if (response.status === 401 || response.status === 403) {
          throw new Error('Your session has expired. Sign in again.')
        }

        if (!response.ok) {
          throw new Error('Could not load incidents.')
        }

        const data: Incident[] = await response.json()

        if (!controller.signal.aborted) {
          setIncidents(data)
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

    void loadIncidents()

    return () => controller.abort()
  }, [reloadKey])

  const visibleIncidents = incidents.filter(
    (incident) => filter === 'all' || incident.status === filter,
  )

  return (
    <section className="dashboard" aria-labelledby="incidents-heading">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">INCIDENT MANAGEMENT</p>
          <h2 id="incidents-heading">Incidents</h2>
        </div>

        <button
          type="button"
          className="refresh-button"
          disabled={loading}
          onClick={() => setReloadKey((value) => value + 1)}
        >
          {loading ? 'Loading…' : 'Refresh incidents'}
        </button>
      </div>

      <div className="incident-filters" aria-label="Filter incidents">
        {(['all', 'open', 'resolved'] as const).map((value) => (
          <button
            type="button"
            key={value}
            className="filter-button"
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {value.charAt(0).toUpperCase() + value.slice(1)}
          </button>
        ))}
      </div>

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {loading && <p role="status">Loading incidents…</p>}

      {!loading && !error && (
        <>
          {visibleIncidents.length === 0 ? (
            <p className="dashboard-note">
              No incidents match this filter.
            </p>
          ) : (
            <div className="monitor-grid">
              {visibleIncidents.map((incident) => (
                <article className="monitor-card" key={incident.id}>
                  <div className="monitor-title">
                    <h3>Incident #{incident.id}</h3>

                    <span
                      className={`status-badge ${
                        incident.status === 'open' ? 'down' : 'up'
                      }`}
                    >
                      {incident.status.toUpperCase()}
                    </span>
                  </div>

                  <p className="incident-title">{incident.title}</p>

                  <dl className="incident-details">
                    <dt>Application</dt>
                    <dd>{incident.application_name}</dd>

                    <dt>Monitor</dt>
                    <dd>{incident.monitor_name}</dd>

                    <dt>Opened</dt>
                    <dd>
                      {new Date(incident.opened_at).toLocaleString()}
                    </dd>

                    <dt>Resolved</dt>
                    <dd>
                      {incident.resolved_at
                        ? new Date(
                            incident.resolved_at,
                          ).toLocaleString()
                        : 'Awaiting recovery'}
                    </dd>
                  </dl>
                </article>
              ))}
            </div>
          )}

          <p className="dashboard-note">
            Incidents open after failed checks and resolve after recovery.
            Select Refresh incidents to load the latest records.
          </p>
        </>
      )}
    </section>
  )
}