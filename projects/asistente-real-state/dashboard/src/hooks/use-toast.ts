import * as React from 'react'
import type { ToastActionElement, ToastProps } from '@/components/ui/toast'

const TOAST_LIMIT = 3
const TOAST_REMOVE_DELAY = 1000000

type ToasterToast = ToastProps & {
  id: string
  title?: React.ReactNode
  description?: React.ReactNode
  action?: ToastActionElement
}

type ActionType = typeof ACTION_TYPES[keyof typeof ACTION_TYPES]

const ACTION_TYPES = {
  ADD_TOAST: 'ADD_TOAST',
  UPDATE_TOAST: 'UPDATE_TOAST',
  DISMISS_TOAST: 'DISMISS_TOAST',
  REMOVE_TOAST: 'REMOVE_TOAST',
} as const

let count = 0
function genId() { return (++count).toString() }

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>()

const addToRemoveQueue = (toastId: string) => {
  if (toastTimeouts.has(toastId)) return
  const timeout = setTimeout(() => {
    toastTimeouts.delete(toastId)
    dispatch({ type: ACTION_TYPES.REMOVE_TOAST, toastId })
  }, TOAST_REMOVE_DELAY)
  toastTimeouts.set(toastId, timeout)
}

type State = { toasts: ToasterToast[] }

function reducer(state: State, action: { type: ActionType; toast?: Partial<ToasterToast>; toastId?: string }): State {
  switch (action.type) {
    case ACTION_TYPES.ADD_TOAST:
      return { ...state, toasts: [action.toast as ToasterToast, ...state.toasts].slice(0, TOAST_LIMIT) }
    case ACTION_TYPES.UPDATE_TOAST:
      return { ...state, toasts: state.toasts.map((t) => t.id === action.toast?.id ? { ...t, ...action.toast } : t) }
    case ACTION_TYPES.DISMISS_TOAST:
      if (action.toastId) addToRemoveQueue(action.toastId)
      else state.toasts.forEach((t) => addToRemoveQueue(t.id))
      return { ...state, toasts: state.toasts.map((t) => (!action.toastId || t.id === action.toastId) ? { ...t, open: false } : t) }
    case ACTION_TYPES.REMOVE_TOAST:
      return { ...state, toasts: action.toastId ? state.toasts.filter((t) => t.id !== action.toastId) : [] }
    default:
      return state
  }
}

const listeners: Array<(state: State) => void> = []
let memoryState: State = { toasts: [] }

function dispatch(action: { type: ActionType; toast?: Partial<ToasterToast>; toastId?: string }) {
  memoryState = reducer(memoryState, action)
  listeners.forEach((l) => l(memoryState))
}

function toast(props: Omit<ToasterToast, 'id'>) {
  const id = genId()
  const dismiss = () => dispatch({ type: ACTION_TYPES.DISMISS_TOAST, toastId: id })
  dispatch({ type: ACTION_TYPES.ADD_TOAST, toast: { ...props, id, open: true, onOpenChange: (open) => { if (!open) dismiss() } } })
  return { id, dismiss, update: (p: ToasterToast) => dispatch({ type: ACTION_TYPES.UPDATE_TOAST, toast: { ...p, id } }) }
}

function useToast() {
  const [state, setState] = React.useState<State>(memoryState)
  React.useEffect(() => {
    listeners.push(setState)
    return () => { const idx = listeners.indexOf(setState); if (idx > -1) listeners.splice(idx, 1) }
  }, [])
  return { ...state, toast, dismiss: (id?: string) => dispatch({ type: ACTION_TYPES.DISMISS_TOAST, toastId: id }) }
}

export { useToast, toast }
