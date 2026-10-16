import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

export type MonitorConfig = {
  id: number
  name: string
  environment: number
  environment_name: string
  url: string
  expected_status_code: number
  check_interval_seconds: number
  timeout_seconds: number
  is_active: boolean
}

type Environment = {
  id: number
  application_name: string
  kind: string
  is_active: boolean
}

type Props = {
  monitor: MonitorConfig | null
  onSaved: (monitor: MonitorConfig) => void
  onCancel: () => void
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
    let message = `Request failed (${response.status}).`

    if (data && typeof data === 'object') {
      message = Object.entries(data)
        .map(([field, value]) => {
          const text = Array.isArray(value)
            ? value.join(' ')
            : String(value)

          return field === 'detail' ? text : `${field}: ${text}`
        })
        .join(' / ')
    }

    throw new Error(message)
  }

  return data as T
}

export default function MonitorForm({
  monitor,
  onSaved,
  onCancel,
}: Props) {
  const [environments, setEnvironments] = useState<Environment[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [form, setForm] = useState(() => ({
    name: monitor?.name ?? '',
    environment: monitor ? String(monitor.environment) : '',
    url: monitor?.url ?? '',
    expected_status_code: String(monitor?.expected_status_code ?? 200),
    check_interval_seconds: String(
      monitor?.check_interval_seconds ?? 60,
    ),
    timeout_seconds: String(monitor?.timeout_seconds ?? 10),
    is_active: monitor?.is_active ?? true,
  }))

  useEffect(() => {
    const controller = new AbortController()

    async function loadEnvironments() {
      setLoading(true)
      setError('')

      try {
        const data = await request<Environment[]>(
          '/api/environments/',
          { signal: controller.signal },
        )

        if (!controller.signal.aborted) {
          setEnvironments(data)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load environments.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadEnvironments()

    return () => controller.abort()
  }, [reloadKey])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')

    try {
      const csrf = await request<{ csrfToken: string }>(
        '/api/auth/csrf/',
      )

      const saved = await request<MonitorConfig>(
        monitor
          ? `/api/monitors/${monitor.id}/`
          : '/api/monitors/',
        {
          method: monitor ? 'PATCH' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({
            name: form.name.trim(),
            environment: Number(form.environment),
            url: form.url.trim(),
            expected_status_code: Number(form.expected_status_code),
            check_interval_seconds: Number(form.check_interval_seconds),
            timeout_seconds: Number(form.timeout_seconds),
            is_active: form.is_active,
          }),
        },
      )

      onSaved(saved)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Could not save monitor.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="application-form-card">
      <h3>{monitor ? 'Edit monitor' : 'Add monitor'}</h3>

      {loading && <p role="status">Loading environments...</p>}

      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}

      {!loading && environments.length === 0 && (
        <p className="dashboard-note">
          No environments available. Create an environment first,
          or refresh if one was recently added.
        </p>
      )}

      <button
        type="button"
        className="secondary-button"
        disabled={loading || saving}
        onClick={() => setReloadKey((value) => value + 1)}
      >
        Refresh environments
      </button>

      <form onSubmit={handleSubmit}>
        <fieldset
          className="application-fields"
          disabled={loading || saving || environments.length === 0}
        >
          <label htmlFor="monitor-name">Monitor name</label>
          <input
            id="monitor-name"
            value={form.name}
            minLength={2}
            maxLength={150}
            required
            onChange={(event) =>
              setForm({ ...form, name: event.target.value })
            }
          />

          <label htmlFor="monitor-environment">Environment</label>
          <select
            id="monitor-environment"
            value={form.environment}
            disabled={monitor !== null}
            required
            onChange={(event) =>
              setForm({ ...form, environment: event.target.value })
            }
          >
            <option value="">Select an environment</option>

            {environments.map((environment) => (
              <option key={environment.id} value={environment.id}>
                {environment.application_name} / {environment.kind}
                {environment.is_active ? '' : ' (inactive)'}
              </option>
            ))}
          </select>

          {monitor && (
            <p className="field-help">
              Existing monitors cannot move to another environment.
            </p>
          )}

          <label htmlFor="monitor-url">Check URL</label>
          <input
            id="monitor-url"
            type="url"
            value={form.url}
            maxLength={2048}
            placeholder="https://example.com/health/"
            required
            onChange={(event) =>
              setForm({ ...form, url: event.target.value })
            }
          />

          <label htmlFor="monitor-status">Expected HTTP status</label>
          <input
            id="monitor-status"
            type="number"
            min={100}
            max={599}
            step={1}
            value={form.expected_status_code}
            required
            onChange={(event) =>
              setForm({
                ...form,
                expected_status_code: event.target.value,
              })
            }
          />

          <label htmlFor="monitor-interval">Check interval (seconds)</label>
          <input
            id="monitor-interval"
            type="number"
            min={30}
            max={86400}
            step={1}
            value={form.check_interval_seconds}
            required
            onChange={(event) =>
              setForm({
                ...form,
                check_interval_seconds: event.target.value,
              })
            }
          />

          <p className="field-help">
            Interval is saved for scheduled monitoring.
            Automatic checks are not enabled yet.
          </p>

          <label htmlFor="monitor-timeout">Timeout (seconds)</label>
          <input
            id="monitor-timeout"
            type="number"
            min={1}
            max={30}
            step={1}
            value={form.timeout_seconds}
            required
            onChange={(event) =>
              setForm({
                ...form,
                timeout_seconds: event.target.value,
              })
            }
          />

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                setForm({ ...form, is_active: event.target.checked })
              }
            />
            Monitor enabled
          </label>

          <button type="submit">
            {saving
              ? 'Saving...'
              : monitor
                ? 'Save changes'
                : 'Create monitor'}
          </button>
        </fieldset>
      </form>

      <button
        type="button"
        className="secondary-button"
        disabled={saving}
        onClick={onCancel}
      >
        Cancel
      </button>
    </section>
  )
}