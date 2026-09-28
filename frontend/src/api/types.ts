export interface User {
  id: number
  email: string
  username: string
  created_at: string
  settings: Record<string, unknown>
}

export interface Token {
  access_token: string
  token_type: string
}

export interface Garden {
  id: number
  name: string
  created_at: string
  updated_at: string
}
