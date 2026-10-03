import { useState } from 'react'

export function IdentityGate({ onSubmit }: { onSubmit: (name: string) => void }) {
  const [name, setName] = useState('')
  return (
    <div className="flex min-h-screen items-center justify-center bg-ink p-6">
      <form
        className="w-full max-w-sm rounded-3xl border border-white/10 bg-panel p-8 text-center"
        onSubmit={(e) => {
          e.preventDefault()
          if (name.trim()) onSubmit(name.trim())
        }}
      >
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-from to-accent-to text-3xl">
          🎙️
        </div>
        <h1 className="text-2xl font-black tracking-tight text-white">РАЦИЯ</h1>
        <p className="mt-1 text-sm text-white/50">Ближе. Где бы вы ни были.</p>
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Как вас зовут?"
          className="mt-6 w-full rounded-xl border border-white/10 bg-card px-4 py-3 text-white outline-none placeholder:text-white/30 focus:border-accent-from"
        />
        <button
          type="submit"
          disabled={!name.trim()}
          className="mt-4 w-full rounded-xl bg-gradient-to-r from-accent-from to-accent-to py-3 font-semibold text-white disabled:opacity-40"
        >
          Войти
        </button>
      </form>
    </div>
  )
}
