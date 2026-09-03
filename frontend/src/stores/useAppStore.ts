/**
 * 全局应用状态管理
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  // 主题
  theme: 'light' | 'dark'
  setTheme: (theme: 'light' | 'dark') => void

  // 侧边栏
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void

  // 全局加载
  globalLoading: boolean
  setGlobalLoading: (loading: boolean) => void

  // 用户偏好
  preferences: {
    showHistory: boolean
    enableLongThinking: boolean
    maxThinkingTime: number
    defaultProvider: string
    defaultModel: string
  }
  updatePreferences: (prefs: Partial<AppState['preferences']>) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // 主题
      theme: 'light',
      setTheme: (theme) => set({ theme }),

      // 侧边栏
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // 全局加载
      globalLoading: false,
      setGlobalLoading: (loading) => set({ globalLoading: loading }),

      // 用户偏好
      preferences: {
        showHistory: true,
        enableLongThinking: true,
        maxThinkingTime: 600,
        defaultProvider: 'bupt',
        defaultModel: 'qwen-medium',
      },
      updatePreferences: (prefs) =>
        set((state) => ({
          preferences: { ...state.preferences, ...prefs },
        })),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        preferences: state.preferences,
      }),
    }
  )
)
