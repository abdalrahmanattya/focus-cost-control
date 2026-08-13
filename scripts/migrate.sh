#!/bin/sh
set -eu
python -c 'import os, pathlib, time
import psycopg
url=os.environ["DATABASE_URL"]
for _ in range(30):
 try:
  with psycopg.connect(url) as c:
   for p in sorted(pathlib.Path("migrations").glob("*.sql")): c.execute(p.read_text())
  break
 except psycopg.OperationalError:
  time.sleep(2)
else: raise SystemExit("database did not become ready")'
