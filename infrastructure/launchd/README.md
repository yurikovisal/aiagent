# Autostart on the Mac mini (§61)

Two options — pick one, don't run both:

## Option A: launchd (native processes, matches `make dev`)

1. Run `make setup && make migrate && make seed` once.
2. Edit the two `.plist` files here, replacing `/path/to/meza` with the real
   checkout path and pointing `ProgramArguments`/`WorkingDirectory` at the
   correct Python venv / npm install.
3. `mkdir -p storage/logs`
4. `cp *.plist ~/Library/LaunchAgents/`
5. `launchctl load ~/Library/LaunchAgents/com.atonplus.meza.api.plist`
6. `launchctl load ~/Library/LaunchAgents/com.atonplus.meza.web.plist`

Ollama itself is usually started the same way it already runs on the
machine (its own installer sets up a launch agent), or add a third plist
for `ollama serve` if it doesn't.

## Option B: Docker Compose restart policy

If Docker Desktop is installed and set to start on login, `docker compose up
-d` (using the root `docker-compose.yml`) with `restart: unless-stopped` on
every service (already set) achieves the same effect without launchd.

Do not combine both — pick native (A) or Docker (B) so the API isn't
double-bound to port 8000.
