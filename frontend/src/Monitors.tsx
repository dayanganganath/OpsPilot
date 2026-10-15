import { useEffect, useState } from 'react'

type Monitor = {
  id: number
  name: string
  environment_name: string
  url: string
  expected_status_code: number
  is_active: boolean
}

type CheckResult = {
  id: number
  monitor: number
  checked_url: string
  expected_status_code: number
  status: 'up' | 'down' | 'error'
  status_code: number | null
  response_time_ms: number
  error_message: string
  checked_at: string
}

async function request<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: 'same-origin',
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(
      data?.detail || `Request failed (${response.status}).`,
    )
  }

  return data as T
}

function MonitorHistory({
  monitor,
  refreshKey,
  onClose,
}: {
  monitor: Monitor
  refreshKey: number
  onClose: () => void
}) {
  const [checks, setChecks] = useState<CheckResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadHistory() {
      setLoading(true)
      setError('')

      try {
        const data = await request<CheckResult[]>(
          `/api/monitors/${monitor.id}/history/`,
          { signal: controller.signal },
        )

        if (!controller.signal.aborted) {
          setChecks(data)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load history.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadHistory()

    return () => controller.abort()
  }, [monitor.id, refreshKey, retryKey])

  return (
    <section
      className="history-panel"
      aria-labelledby="history-heading"
    >
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">SAVED CHECKS</p>
          <h2 id="history-heading">{monitor.name}: history</h2>
        </div>

        <div className="monitor-actions">
          <button
            type="button"
            className="refresh-button"
            disabled={loading}
            onClick={() => setRetryKey((value) => value + 1)}
          >
            Refresh
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>

      {loading && <p role="status">Loading history...</p>}

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && (
        <>
          {checks.length === 0 ? (
            <p className="dashboard-note">
              No saved checks yet. Select Check now to create one.
            </p>
          ) : (
            <div
              className="history-table-wrap"
              role="region"
              aria-label="Monitor check history"
              tabIndex={0}
            >
              <table className="history-table">
                <caption>
                  Latest {checks.length} saved checks, newest first.
                  Up to 100 records are shown.
                </caption>

                <thead>
                  <tr>
                    <th scope="col">Checked at</th>
                    <th scope="col">Status</th>
                    <th scope="col">HTTP</th>
                    <th scope="col">Expected</th>
                    <th scope="col">Time</th>
                    <th scope="col">Checked URL</th>
                    <th scope="col">Error</th>
                  </tr>
                </thead>

                <tbody>
                  {checks.map((check) => (
                    <tr key={check.id}>
                      <td>
                        {new Date(check.checked_at).toLocaleString()}
                      </td>
                      <td>
                        <span
                          className={`status-badge ${check.status}`}
                        >
                          {check.status.toUpperCase()}
                        </span>
                      </td>
                      <td>{check.status_code ?? '-'}</td>
                      <td>{check.expected_status_code}</td>
                      <td>
                        {check.response_time_ms.toFixed(2)} ms
                      </td>
                      <td className="history-url">
                        {check.checked_url}
                      </td>
                      <td>{check.error_message || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default function Monitors() {
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [results, setResults] = useState<
    Record<number, CheckResult>
  >({})
  const [loading, setLoading] = useState(true)
  const [runningId, setRunningId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [selectedMonitor, setSelectedMonitor] =
    useState<Monitor | null>(null)
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadMonitors() {
      setLoading(true)
      setError('')

      try {
        const data = await request<Monitor[]>('/api/monitors/', {
          signal: controller.signal,
        })

        if (!controller.signal.aborted) {
          setMonitors(data)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load monitors.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadMonitors()

    return () => controller.abort()
  }, [reloadKey])

  async function checkNow(monitorId: number) {
    setRunningId(monitorId)
    setError('')

    try {
      const csrf = await request<{ csrfToken: string }>(
        '/api/auth/csrf/',
      )

      const result = await request<CheckResult>(
        `/api/monitors/${monitorId}/check-now/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({}),
        },
      )

      setResults((previous) => ({
        ...previous,
        [monitorId]: result,
      }))

      setHistoryRefreshKey((value) => value + 1)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Check failed.',
      )
    } finally {
      setRunningId(null)
    }
  }

  return (
    <section className="dashboard" aria-labelledby="monitors-heading">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">SERVICE MONITORING</p>
          <h2 id="monitors-heading">Monitors</h2>
        </div>

        <button
          type="button"
          className="refresh-button"
          disabled={loading || runningId !== null}
          onClick={() => setReloadKey((value) => value + 1)}
        >
          Refresh list
        </button>
      </div>

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p role="status">Loading monitors...</p>
      ) : (
        <>
          {monitors.length === 0 && (
            <p className="dashboard-note">
              No monitors found for your account.
            </p>
          )}

          <div className="monitor-grid">
            {monitors.map((monitor) => {
              const result = results[monitor.id]
              const running = runningId === monitor.id
              const historyOpen =
                selectedMonitor?.id === monitor.id

              return (
                <article className="monitor-card" key={monitor.id}>
                  <div className="monitor-title">
                    <h3>{monitor.name}</h3>

                    <span
                      className={`status-badge ${
                        monitor.is_active ? 'up' : 'inactive'
                      }`}
                    >
                      {monitor.is_active ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>

                  <p className="dashboard-note">
                    {monitor.environment_name}
                  </p>

                  <p className="monitor-url">{monitor.url}</p>

                  <p className="dashboard-note">
                    Expected HTTP {monitor.expected_status_code}
                  </p>

                  <div className="check-result" aria-live="polite">
                    {running ? (
                      <p>Checking service...</p>
                    ) : result ? (
                      <>
                        <span
                          className={`status-badge ${result.status}`}
                        >
                          {result.status.toUpperCase()}
                        </span>

                        <p>
                          HTTP {result.status_code ?? '-'} /{' '}
                          {result.response_time_ms.toFixed(2)} ms
                        </p>

                        <p className="dashboard-note">
                          {new Date(result.checked_at).toLocaleString()}
                        </p>

                        {result.error_message && (
                          <p>{result.error_message}</p>
                        )}
                      </>
                    ) : (
                      <p className="dashboard-note">
                        Run a check for a result, or open saved history.
                      </p>
                    )}
                  </div>

                  <div className="monitor-actions">
                    <button
                      type="button"
                      disabled={
                        !monitor.is_active || runningId !== null
                      }
                      onClick={() => void checkNow(monitor.id)}
                    >
                      {running ? 'Checking...' : 'Check now'}
                    </button>

                    <button
                      type="button"
                      className="secondary-button"
                      aria-expanded={historyOpen}
                      onClick={() =>
                        setSelectedMonitor(
                          historyOpen ? null : monitor,
                        )
                      }
                    >
                      {historyOpen ? 'Hide history' : 'History'}
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        </>
      )}

      {selectedMonitor && (
        <MonitorHistory
          key={selectedMonitor.id}
          monitor={selectedMonitor}
          refreshKey={historyRefreshKey}
          onClose={() => setSelectedMonitor(null)}
        />
      )}

      <p className="dashboard-note">
        Card results show checks run on this screen. History loads saved
        records. Refresh dashboard metrics after running a check.
      </p>
    </section>
  )
}