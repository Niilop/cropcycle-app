import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { errorMessage } from '../api/client'
import type { Garden } from '../api/types'
import { useAuth } from '../auth/context'

// Minimal web view kept until the Expo app replaces this frontend (plan 002, Phase 5).
export function GardensPage() {
  const { request } = useAuth()
  const [gardens, setGardens] = useState<Garden[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [pending, setPending] = useState(false)
  const [name, setName] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    void request<Garden[]>('/gardens', { signal })
      .then((data) => {
        if (!signal.aborted) setGardens(data)
      })
      .catch((error: unknown) => {
        if (!signal.aborted) setLoadError(errorMessage(error))
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [request])

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError('')
    setNotice('')
    try {
      const garden = await request<Garden>('/gardens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      setGardens((current) => [...current, garden])
      setName('')
      setNotice('Garden created.')
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setPending(false)
    }
  }

  return (
    <>
      <div className="page-heading">
        <p className="eyebrow">CropCycle</p>
        <h1>Your gardens</h1>
        <p>Bed layouts, history and plans are managed in the CropCycle app.</p>
      </div>
      <div className="overview-grid">
        <section className="panel" aria-busy={loading}>
          <h2>Gardens</h2>
          {loadError && (
            <p className="notice error" role="alert">
              {loadError}
            </p>
          )}
          {!loading && !loadError && gardens.length === 0 && <h3>No gardens yet</h3>}
          <ul>
            {gardens.map((garden) => (
              <li key={garden.id}>{garden.name}</li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <h2>Add a garden</h2>
          <form onSubmit={create}>
            <label htmlFor="garden-name">Name</label>
            <input
              id="garden-name"
              required
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            {error && (
              <p className="notice error" role="alert">
                {error}
              </p>
            )}
            {notice && (
              <p className="notice success" role="status">
                {notice}
              </p>
            )}
            <button disabled={pending || !name.trim()}>
              {pending ? 'Saving…' : 'Create garden'}
            </button>
          </form>
        </section>
      </div>
    </>
  )
}
