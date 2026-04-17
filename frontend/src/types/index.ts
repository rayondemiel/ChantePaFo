export interface Player {
  id: string
  name: string
  is_host: boolean
}

export interface RoomSettings {
  game_mode: 'blindtest' | 'karaoke' | 'telephone'
  genres: Record<string, number>
  num_rounds: number
  extract_duration: number
  karaoke_variant: 'classic' | 'progressive' | 'mystery'
}

export interface RoomState {
  code: string
  players: Player[]
  settings: RoomSettings
  status: 'lobby' | 'playing' | 'closed'
}

export interface Winner {
  player_id: string
  name: string
  time_ms: number
}

export interface MatchInfo {
  player_id: string
  name: string
  time_ms: number
  match_type: 'title' | 'artist' | 'bonus'
}

export interface GameState {
  phase: string
  current_round: number
  total_rounds: number
  total_scores: Record<string, number>
  track?: { preview_url: string; genre: string; cover_url?: string }
  round_results?: {
    correct_title: string
    correct_artist: string
    cover_url?: string
    winners?: Winner[]
    all_matches?: MatchInfo[]
  }
  round_scores?: Record<string, number>
  extract_duration?: number
  [key: string]: unknown
}

export interface PlayerFoundEvent {
  player_id: string
  time_ms: number
  match_type?: 'title' | 'artist' | 'bonus'
}

export interface AmbianceConfig {
  palette: string[]
  behavior: string
  intensity: number
  vibe: string
  bpm?: number
}

export interface Award {
  id: string
  title: string
  emoji: string
  player_id: string
  player_name: string
  detail: string
}

export interface FuzzyResult {
  title_match: boolean
  artist_match: boolean
  bonus: boolean
  distance: number
}
