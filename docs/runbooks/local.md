# Local runbook

Run the test command from the README, start Uvicorn, then call `/health` and `/api/v1/summary`. For CSV imports, use a UTF-8 file with the six required FOCUS columns. Stop the server with Ctrl-C. Do not place provider credentials in `.env` or fixtures.

For a full Compose drill, run `FOCUS_API_PORT=18000 scripts/e2e.sh`. It builds the API/dashboard images, waits for PostgreSQL migrations, uploads the synthetic fixture, checks asynchronous completion, restarts the API, verifies the imported record remains, and runs the retry/dead-letter tests. The drill removes its temporary Compose volume on exit.
