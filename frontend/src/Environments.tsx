import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

type Application = {
  id: number
  name: string
  is_active: boolean
}

type EnvironmentKind = 'development' | 'staging' | 'production'

type Environment = {
  id: number
  application: number
  application_name: string
  kind: EnvironmentKind
  base_url: string
  is_active: boolean
}

type EnvironmentForm = {
  application: string
  kind: EnvironmentKind
  base_url: string
  is_active: boolean
}

const emptyForm: EnvironmentForm = {
  application: '',
  kind: 'development',
  base_url: '',
  is_active: true,
}

const kindLabels: Record<EnvironmentKind, string> = {
  development: 'Development',
  staging: 'Staging',
  production: 'Production',
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

export default function Environments() {
  const [applications, setApplications] = useState<Application[]>([])
  const [environments, setEnvironments] = useState<Environment[]>([])
  const [form, setForm] = useState<EnvironmentForm>(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadData() {
      setLoading(true)
      setError('')

      try {
        const [applicationData, environmentData] = await Promise.all([
          request<Application[]>('/api/applications/', {
            signal: controller.signal,
          }),
          request<Environment[]>('/api/environments/', {
            signal: controller.signal,
          }),
        ])

        if (!controller.signal.aborted) {
          setApplications(applicationData)
          setEnvironments(environmentData)
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

    void loadData()

    return () => controller.abort()
  }, [reloadKey])

  function resetForm() {
    setForm({ ...emptyForm })
    setEditingId(null)
  }

  function editEnvironment(environment: Environment) {
    setEditingId(environment.id)

    setForm({
      application: String(environment.application),
      kind: environment.kind,
      base_url: environment.base_url,
      is_active: environment.is_active,
    })

    setError('')
    setSuccess('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')

    const wasEditing = editingId !== null

    try {
      const csrf = await request<{ csrfToken: string }>(
        '/api/auth/csrf/',
      )

      const saved = await request<Environment>(
        wasEditing
          ? `/api/environments/${editingId}/`
          : '/api/environments/',
        {
          method: wasEditing ? 'PATCH' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({
            application: Number(form.application),
            kind: form.kind,
            base_url: form.base_url.trim(),
            is_active: form.is_active,
          }),
        },
      )

      setEnvironments((previous) => {
        const updated = wasEditing
          ? previous.map((item) =>
              item.id === saved.id ? saved : item,
            )
          : [...previous, saved]

        return updated.sort(
          (a, b) =>
            a.application_name.localeCompare(b.application_name) ||
            a.kind.localeCompare(b.kind),
        )
      })

      resetForm()

      setSuccess(
        wasEditing
          ? 'Environment updated successfully.'
          : 'Environment created successfully.',
      )
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not save environment.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section
      className="dashboard"
      aria-labelledby="environments-heading"
    >
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">DEPLOYMENT ENVIRONMENTS</p>
          <h2 id="environments-heading">Environments</h2>
        </div>

        <button
          type="button"
          className="refresh-button"
          disabled={loading || saving}
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

      {success && (
        <p className="success-message" role="status">
          {success}
        </p>
      )}

      <div className="application-layout">
        <section className="application-form-card">
          <h3>
            {editingId !== null ? 'Edit environment' : 'Add environment'}
          </h3>

          {!loading && applications.length === 0 && (
            <p className="dashboard-note">
              Create an application first, then add its environments.
            </p>
          )}

          <form onSubmit={handleSubmit}>
            <fieldset
              className="application-fields"
              disabled={
                saving || loading || applications.length === 0
              }
            >
              <label htmlFor="environment-application">
                Application
              </label>

              <select
                id="environment-application"
                value={form.application}
                disabled={editingId !== null}
                required
                onChange={(event) =>
                  setForm({
                    ...form,
                    application: event.target.value,
                  })
                }
              >
                <option value="">Select an application</option>

                {applications.map((application) => (
                  <option key={application.id} value={application.id}>
                    {application.name}
                    {application.is_active ? '' : ' (inactive)'}
                  </option>
                ))}
              </select>

              {editingId !== null && (
                <p className="field-help">
                  An existing environment cannot move to another
                  application.
                </p>
              )}

              <label htmlFor="environment-kind">Environment kind</label>

              <select
                id="environment-kind"
                value={form.kind}
                onChange={(event) =>
                  setForm({
                    ...form,
                    kind: event.target.value as EnvironmentKind,
                  })
                }
              >
                <option value="development">Development</option>
                <option value="staging">Staging</option>
                <option value="production">Production</option>
              </select>

              <label htmlFor="environment-url">
                Base URL (optional)
              </label>

              <input
                id="environment-url"
                type="url"
                value={form.base_url}
                maxLength={200}
                placeholder="https://staging.example.com"
                onChange={(event) =>
                  setForm({
                    ...form,
                    base_url: event.target.value,
                  })
                }
              />

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      is_active: event.target.checked,
                    })
                  }
                />
                Environment active
              </label>

              <div className="monitor-actions">
                <button type="submit">
                  {saving
                    ? 'Saving...'
                    : editingId !== null
                      ? 'Save changes'
                      : 'Create environment'}
                </button>

                {editingId !== null && (
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => {
                      resetForm()
                      setError('')
                    }}
                  >
                    Cancel
                  </button>
                )}
              </div>
            </fieldset>
          </form>
        </section>

        <div>
          {loading ? (
            <p role="status">Loading environments...</p>
          ) : environments.length === 0 ? (
            <p className="dashboard-note">
              No environments yet. Add one using the form.
            </p>
          ) : (
            <div className="application-list">
              {environments.map((environment) => (
                <article
                  className="monitor-card"
                  key={environment.id}
                >
                  <div className="monitor-title">
                    <h3>{environment.application_name}</h3>

                    <span
                      className={`status-badge ${
                        environment.is_active ? 'up' : 'inactive'
                      }`}
                    >
                      {environment.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  <p className="eyebrow">
                    {kindLabels[environment.kind]}
                  </p>

                  <p className="monitor-url">
                    {environment.base_url || 'Base URL not configured'}
                  </p>

                  <button
                    type="button"
                    className="secondary-button"
                    disabled={saving}
                    onClick={() => editEnvironment(environment)}
                  >
                    Edit environment
                  </button>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}