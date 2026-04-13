import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GameState, Award } from '../types'

export const useGameStore = defineStore('game', () => {
  const state = ref<GameState | null>(null)
  const awards = ref<Award[]>([])
  const finalScores = ref<Record<string, number>>({})

  function setState(data: GameState) {
    state.value = data
  }

  function setFinalResults(data: { awards: Award[]; total_scores: Record<string, number> }) {
    awards.value = data.awards
    finalScores.value = data.total_scores
  }

  function reset() {
    state.value = null
    awards.value = []
    finalScores.value = {}
  }

  return { state, awards, finalScores, setState, setFinalResults, reset }
})
