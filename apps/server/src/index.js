import 'dotenv/config'
import { app } from './app.js'

const PORT = process.env.PORT || 8787
app.listen(PORT, () => console.log(`[server] Рация API слушает http://localhost:${PORT}`))
