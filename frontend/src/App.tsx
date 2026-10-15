import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
} from 'react-router-dom'

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

function OpsPilotApp() {
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

  if (!user) {
    return (
      <Routes>
        <Route
          path="/login"
          element={
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
          }
        />

        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    )
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">OP</div>
          <div>
            <strong>OpsPilot</strong>
            <span>Operations workspace</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' active' : ''}`
            }
          >
            <span aria-hidden="true">01</span>
            Dashboard
          </NavLink>

          <NavLink
            to="/monitors"
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' active' : ''}`
            }
          >
            <span aria-hidden="true">02</span>
            Monitors
          </NavLink>

          <NavLink
            to="/incidents"
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' active' : ''}`
            }
          >
            <span aria-hidden="true">03</span>
            Incidents
          </NavLink>
        </nav>

        <div className="sidebar-account">
          <span className="account-label">SIGNED IN AS</span>
          <strong>{user.username}</strong>

          <button
            type="button"
            className="signout-button"
            disabled={busy}
            onClick={() => void handleLogout()}
          >
            {busy ? 'Signing out…' : 'Sign out'}
          </button>

          {error && (
            <p className="error-message" role="alert">
              {error}
            </p>
          )}
        </div>
      </aside>

      <div className="app-main">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">OPSPILOT WORKSPACE</p>
            <p className="workspace-greeting">
              Welcome, {user.username}
            </p>
          </div>

          <span className="workspace-tag">
            Service operations
          </span>
        </header>

        <main className="app-content">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/monitors" element={<Monitors />} />
            <Route path="/incidents" element={<Incidents />} />

            <Route
              path="*"
              element={<Navigate to="/dashboard" replace />}
            />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <OpsPilotApp />
    </BrowserRouter>
  )
}