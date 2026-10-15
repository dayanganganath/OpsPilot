import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import Dashboard from './Dashboard'
import Monitors from './Monitors'
import Incidents from './Incidents'

type User = {
  id: number
  username: string
  email: string
}

type AuthResponse = {
  user: User
}

async function api<T>(
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

async function getCsrfToken(): Promise<string> {
  const data = await api<{ csrfToken: string }>(
    '/api/auth/csrf/',
  )

  return data.csrfToken
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [checkingSession, setCheckingSession] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function checkSession() {
      try {
        const response = await fetch('/api/auth/session/', {
          credentials: 'same-origin',
          signal: controller.signal,
        })

        if (response.status === 401) {
          return
        }

        if (!response.ok) {
          throw new Error('Could not check your session.')
        }

        const data: AuthResponse = await response.json()

        if (!controller.signal.aborted) {
          setUser(data.user)
        }
      } catch {
        if (!controller.signal.aborted) {
          setError(
            'Cannot connect to OpsPilot. Check that the backend is running.',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setCheckingSession(false)
        }
      }
    }

    void checkSession()

    return () => controller.abort()
  }, [])

  async function handleLogin(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()
    setBusy(true)
    setError('')

    try {
      const csrfToken = await getCsrfToken()

      const data = await api<AuthResponse>(
        '/api/auth/login/',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            username: username.trim(),
            password,
          }),
        },
      )

      setUser(data.user)
      setPassword('')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Login failed.',
      )
    } finally {
      setBusy(false)
    }
  }

  async function handleLogout() {
    setBusy(true)
    setError('')

    try {
      const csrfToken = await getCsrfToken()

      await api<{ detail: string }>(
        '/api/auth/logout/',
        {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken,
          },
        },
      )

      setUser(null)
      setUsername('')
      setPassword('')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Logout failed.',
      )
    } finally {
      setBusy(false)
    }
  }

  if (checkingSession) {
    return (
      <main className="auth-page">
        <p role="status">Connecting to OpsPilot…</p>
      </main>
    )
  }

  if (user) {
    return (
      <main className="workspace-page">
        <section className="workspace-card">
          <div className="brand-mark">OP</div>
          <p className="eyebrow">OPSPILOT</p>

          <h1>Welcome, {user.username}</h1>

          <Dashboard />

          <Monitors />

          <Incidents />

          {error && (
            <p className="error-message" role="alert">
              {error}
            </p>
          )}

          <button
            type="button"
            disabled={busy}
            onClick={() => void handleLogout()}
          >
            {busy ? 'Signing out…' : 'Sign out'}
          </button>
        </section>
      </main>
    )
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand-mark">OP</div>
        <p className="eyebrow">OPSPILOT</p>

        <h1>Your operations, in view.</h1>

        <p className="description">
          Sign in to monitor services and manage incidents.
        </p>

        <form onSubmit={handleLogin}>
          <label htmlFor="username">Username</label>

          <input
            id="username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) =>
              setUsername(event.target.value)
            }
            disabled={busy}
            required
          />

          <label htmlFor="password">Password</label>

          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            disabled={busy}
            required
          />

          {error && (
            <p className="error-message" role="alert">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}