import { useEffect, useState } from 'react'
import type { Channel, Identity } from './types'
import { fetchChannels } from './lib/api'
import { loadIdentity, saveIdentity } from './lib/identity'
import { IdentityGate } from './components/IdentityGate'
import { ChannelList } from './components/ChannelList'
import { ChannelView } from './components/ChannelView'
import { socket } from './lib/socket'

export default function App() {
  const [identity, setIdentity] = useState<Identity | null>(() => loadIdentity())
  const [channels, setChannels] = useState<Channel[]>([])
  const [activeChannel, setActiveChannel] = useState<string | null>(null)

  useEffect(() => {
    if (!identity) return
    fetchChannels().then(setChannels)
    const refresh = () => fetchChannels().then(setChannels)
    socket.on('message:new', refresh)
    socket.on('channel:update', refresh)
    return () => {
      socket.off('message:new', refresh)
      socket.off('channel:update', refresh)
    }
  }, [identity])

  if (!identity) {
    return <IdentityGate onSubmit={(name) => setIdentity(saveIdentity(name))} />
  }

  if (activeChannel) {
    return <ChannelView channelId={activeChannel} me={identity} onBack={() => setActiveChannel(null)} />
  }

  return <ChannelList channels={channels} onOpen={setActiveChannel} />
}
