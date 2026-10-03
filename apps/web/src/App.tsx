import { useEffect, useState } from 'react'
import type { Channel, Identity } from './types'
import { fetchChannels } from './lib/api'
import { loadIdentity, saveIdentity } from './lib/identity'
import { IdentityGate } from './components/IdentityGate'
import { ChannelList } from './components/ChannelList'
import { ChannelView } from './components/ChannelView'

const CHANNEL_LIST_POLL_MS = 5000

export default function App() {
  const [identity, setIdentity] = useState<Identity | null>(() => loadIdentity())
  const [channels, setChannels] = useState<Channel[]>([])
  const [activeChannel, setActiveChannel] = useState<string | null>(null)

  useEffect(() => {
    if (!identity || activeChannel) return
    let cancelled = false
    const refresh = () => fetchChannels().then((c) => !cancelled && setChannels(c))
    refresh()
    const interval = setInterval(refresh, CHANNEL_LIST_POLL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [identity, activeChannel])

  if (!identity) {
    return <IdentityGate onSubmit={(name) => setIdentity(saveIdentity(name))} />
  }

  if (activeChannel) {
    return <ChannelView channelId={activeChannel} me={identity} onBack={() => setActiveChannel(null)} />
  }

  return <ChannelList channels={channels} onOpen={setActiveChannel} />
}
