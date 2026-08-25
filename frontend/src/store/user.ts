import storage from './storage'
import proxyWithPersist, { PersistStrategy } from './valtio-persist'

const state = proxyWithPersist({
  name: 'user',
  version: 0,
  getStorage: () => storage,
  persistStrategies: {
    token: PersistStrategy.SingleFile,
    username: PersistStrategy.SingleFile,
  },
  migrations: {},

  initialState: {
    token: null as string | null,
    username: null as string | null,
  },
})

const actions = {
  setToken(token: string) {
    state.token = token
  },
  setUsername(username: string) {
    state.username = username
  },
  logout() {
    state.token = null
    state.username = null
  },
}

export const userState = state
export const userActions = actions
