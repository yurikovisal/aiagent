function seededBars(seed: string, count: number) {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  const bars: number[] = []
  for (let i = 0; i < count; i++) {
    h = (h * 1103515245 + 12345) >>> 0
    bars.push(0.25 + ((h >>> 8) % 100) / 100)
  }
  return bars.map((b) => Math.min(b, 1))
}

export function Waveform({ seed, progress = 0 }: { seed: string; progress?: number }) {
  const bars = seededBars(seed, 28)
  return (
    <div className="flex h-6 flex-1 items-center gap-[2px]">
      {bars.map((h, i) => (
        <span
          key={i}
          className="w-[3px] rounded-full"
          style={{
            height: `${h * 100}%`,
            backgroundColor: i / bars.length <= progress ? '#22c55e' : 'rgba(255,255,255,0.18)',
          }}
        />
      ))}
    </div>
  )
}
