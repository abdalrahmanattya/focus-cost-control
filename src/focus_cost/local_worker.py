"""Visible local worker companion for Compose.

The API's daemon worker owns the in-process queue for credential-free local use.
This companion keeps a PostgreSQL-backed worker slot observable and can be used
as the handoff point when running the external queue adapter locally.
"""
from __future__ import annotations
import os
import time
import psycopg

def main() -> None:
    url = os.environ["DATABASE_URL"]
    while True:
        with psycopg.connect(url) as connection:
            pending = connection.execute("SELECT count(*) FROM import_runs WHERE status IN ('queued','failed')").fetchone()[0]
        print(f"local worker ready; pending durable runs={pending}", flush=True)
        time.sleep(10)

if __name__ == "__main__": main()
