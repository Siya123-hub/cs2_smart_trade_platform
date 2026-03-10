import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/utils/api'
import type { User } from '@/types'

interface UserState {
  user: User | null;
  token: string | null;
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    user: null,
    token: localStorage.getItem('token') || null,
  }),
  getters: {
    isLoggedIn: (state): boolean => !!state.token && !!state.user,
  },
  actions: {
    async login(username: string, password: string) {
      const response: any = await authApi.login(username, password)
      this.token = response.data?.access_token || response.access_token
      localStorage.setItem('token', this.token!)
      await this.fetchCurrentUser()
    },
    async fetchCurrentUser() {
      try {
        const res: any = await authApi.getCurrentUser()
        this.user = res.data || res
      } catch (error) {
        this.logout()
      }
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
    },
  },
})
