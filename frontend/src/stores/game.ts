import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GameState, Award, TracklistEntry } from '../types'

export const useGameStore = defineStore('game', () => {
  const state = ref<GameState | null>(null)
  const awards = ref<Award[]>([])
  const finalScores = ref<Record<string, number>>({})
  const tracklist = ref<TracklistEntry[]>([])

  function setState(data: GameState) {
    state.value = data
  }

  function setFinalResults(data: {
    awards: Award[]
    total_scores: Record<string, number>
    tracklist?: TracklistEntry[]
  }) {
    awards.value = data.awards
    finalScores.value = data.total_scores
    tracklist.value = data.tracklist ?? []
  }

  function reset() {
    state.value = null
    awards.value = []
    finalScores.value = {}
    tracklist.value = []
  }

  return { state, awards, finalScores, tracklist, setState, setFinalResults, reset }
})
