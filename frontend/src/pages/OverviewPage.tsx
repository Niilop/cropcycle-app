import { Link } from 'react-router'
import { useAuth } from '../auth/context'

export function OverviewPage() {
  const { session } = useAuth()
  return (
    <div className="page-heading">
      <p className="eyebrow">Crop rotation planner</p>
      <h1>{session ? `Welcome, ${session.user.username}.` : 'Plan what grows where.'}</h1>
      <p>
        Record what grew in each bed, choose next season’s crops, and let CropCycle suggest the
        rest.
      </p>
      <Link className="text-link" to={session ? '/gardens' : '/register'}>
        {session ? 'Open your gardens' : 'Create an account'} <span aria-hidden="true">→</span>
      </Link>
    </div>
  )
}
