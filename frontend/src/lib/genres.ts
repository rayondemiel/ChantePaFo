/**
 * Shared genre metadata used by both the host's GenreSelector
 * (interactive editor) and the spectator waiting state (read-only display).
 *
 * The `color` field maps to one of the `.chip-*` classes from
 * assets/global.css, keeping the two views visually consistent.
 */
export interface GenreMeta {
  key: string
  label: string
  color: string
}

export const GENRES: ReadonlyArray<GenreMeta> = [
  { key: 'all', label: 'Tout', color: 'pop' },
  { key: 'pop', label: 'Pop', color: 'pop' },
  { key: 'rock', label: 'Rock', color: 'rock' },
  { key: 'rap', label: 'Rap FR', color: 'rap' },
  { key: 'electro', label: 'Electro', color: 'electro' },
  { key: 'disco', label: 'Disco', color: 'disco' },
  { key: 'jazz', label: 'Jazz', color: 'jazz' },
  { key: 'soul', label: 'Soul/Funk', color: 'disco' },
  { key: 'metal', label: 'Metal', color: 'rock' },
  { key: 'kpop', label: 'K-pop', color: 'pop' },
  { key: 'annees80', label: '80s', color: 'electro' },
  { key: 'annees90', label: '90s', color: 'electro' },
  { key: 'classique', label: 'Classique', color: 'jazz' },
  { key: 'rnb', label: 'R&B', color: 'rap' },
  { key: 'reggae', label: 'Reggae', color: 'disco' },
  { key: 'latino', label: 'Latino', color: 'disco' },
  { key: 'bo_films', label: 'BO Films', color: 'jazz' },
]

const GENRE_MAP = new Map(GENRES.map((g) => [g.key, g]))

export function getGenreMeta(key: string): GenreMeta | undefined {
  return GENRE_MAP.get(key)
}

export function getGenreLabel(key: string): string {
  return GENRE_MAP.get(key)?.label ?? key
}

export function getGenreColor(key: string): string {
  return GENRE_MAP.get(key)?.color ?? 'pop'
}

export const DIFFICULTY_LABELS = ['Facile', 'Normal', 'Difficile', 'Expert'] as const
