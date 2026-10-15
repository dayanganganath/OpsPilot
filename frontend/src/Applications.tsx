import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

type Application = {
  id: number
  name: string
  slug: string
  description: string
  repository_url: string
  owner_username: string
  is_active: boolean
}

type ApplicationForm = {
  name: string
  slug: string
  description: string
  repository_url: string
  is_active: boolean
}

const emptyForm: ApplicationForm = {
  name: '',
  slug: '',
  description: '',
  repository_url: '',
  is_active: true,
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

export default function Applications() {
  const [applications, setApplications] = useState<Application[]>([])
  const [form, setForm] = useState<ApplicationForm>(emptyForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadApplications() {
      setLoading(true)
      setError('')

      try {
        const data = await request<Application[]>(
          '/api/applications/',
          { signal: controller.signal },
        )

        if (!controller.signal.aborted) {
          setApplications(data)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load applications.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadApplications()

    return () => controller.abort()
  }, [reloadKey])

  function resetForm() {
    setForm({ ...emptyForm })
    setEditingId(null)
  }

  function editApplication(application: Application) {
    setEditingId(application.id)
    setForm({
      name: application.name,
      slug: application.slug,
      description: application.description,
      repository_url: application.repository_url,
      is_active: application.is_active,
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

      const saved = await request<Application>(
        wasEditing
          ? `/api/applications/${editingId}/`
          : '/api/applications/',
        {
          method: wasEditing ? 'PATCH' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({
            ...form,
            name: form.name.trim(),
            slug: form.slug.trim(),
            repository_url: form.repository_url.trim(),
          }),
        },
      )

      setApplications((previous) => {
        const updated = wasEditing
          ? previous.map((item) =>
              item.id === saved.id ? saved : item,
            )
          : [...previous, saved]

        return updated.sort((a, b) => a.name.localeCompare(b.name))
      })

      resetForm()
      setSuccess(
        wasEditing
          ? 'Application updated successfully.'
          : 'Application created successfully.',
      )
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not save application.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="dashboard" aria-labelledby="applications-heading">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">APPLICATION MANAGEMENT</p>
          <h2 id="applications-heading">Applications</h2>
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
            {editingId !== null ? 'Edit application' : 'Add application'}
          </h3>

          <form onSubmit={handleSubmit}>
            <fieldset className="application-fields" disabled={saving || loading}>
              <label htmlFor="application-name">Application name</label>
              <input
                id="application-name"
                value={form.name}
                minLength={2}
                maxLength={150}
                required
                onChange={(event) =>
                  setForm({ ...form, name: event.target.value })
                }
              />

              <label htmlFor="application-slug">Unique slug</label>
              <input
                id="application-slug"
                value={form.slug}
                maxLength={150}
                pattern="[-a-zA-Z0-9_]+"
                aria-describedby="slug-help"
                required
                onChange={(event) =>
                  setForm({ ...form, slug: event.target.value })
                }
              />
              <p id="slug-help" className="field-help">
                Example: payment-api. Use letters, numbers, hyphens
                or underscores.
              </p>

              <label htmlFor="application-description">Description</label>
              <textarea
                id="application-description"
                rows={4}
                value={form.description}
                onChange={(event) =>
                  setForm({
                    ...form,
                    description: event.target.value,
                  })
                }
              />

              <label htmlFor="application-repository">
                Repository URL (optional)
              </label>
              <input
                id="application-repository"
                type="url"
                value={form.repository_url}
                maxLength={200}
                placeholder="https://github.com/owner/repository"
                onChange={(event) =>
                  setForm({
                    ...form,
                    repository_url: event.target.value,
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
                Application active
              </label>

              <div className="monitor-actions">
                <button type="submit">
                  {saving
                    ? 'Saving...'
                    : editingId !== null
                      ? 'Save changes'
                      : 'Create application'}
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
            <p role="status">Loading applications...</p>
          ) : applications.length === 0 ? (
            <p className="dashboard-note">
              No applications yet. Create your first application
              using the form.
            </p>
          ) : (
            <div className="application-list">
              {applications.map((application) => (
                <article className="monitor-card" key={application.id}>
                  <div className="monitor-title">
                    <h3>{application.name}</h3>
                    <span
                      className={`status-badge ${
                        application.is_active ? 'up' : 'inactive'
                      }`}
                    >
                      {application.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  <p className="dashboard-note">{application.slug}</p>

                  {application.description && (
                    <p className="application-description">
                      {application.description}
                    </p>
                  )}

                  {application.repository_url && (
                    <p className="monitor-url">
                      {application.repository_url}
                    </p>
                  )}

                  <p className="dashboard-note">
                    Owner: {application.owner_username}
                  </p>

                  <button
                    type="button"
                    className="secondary-button"
                    disabled={saving}
                    onClick={() => editApplication(application)}
                  >
                    Edit application
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