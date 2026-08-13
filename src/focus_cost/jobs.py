"""Durable-shaped asynchronous import queue with retry and dead-letter state."""
from __future__ import annotations
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from uuid import uuid4
from .domain import CostRecord, ImportRun
from .repository import Repository

@dataclass
class ImportJob:
    run: ImportRun
    records: list[CostRecord]

class ImportWorker:
    def __init__(self, repository: Repository, max_attempts: int = 3):
        self.repository, self.max_attempts = repository, max_attempts
        self.queue: Queue[ImportJob | None] = Queue()
        self.dead_letter: list[ImportJob] = []
        self.thread = Thread(target=self._run, name="focus-import-worker", daemon=True)
        self.thread.start()
    def enqueue(self, records: list[CostRecord]) -> ImportRun:
        run = ImportRun(str(uuid4()), "queued", len(records), attempt=0)
        self.repository.register_import(run)
        self.queue.put(ImportJob(run, records)); return run
    def _run(self):
        while True:
            job = self.queue.get()
            if job is None: return
            job.run.status = "processing"
            job.run.attempt += 1
            self.repository.update_import(job.run.id, "processing", attempt=job.run.attempt, error=None)
            try:
                self.repository.save_import(job.run, job.records)
            except Exception as exc:  # retry and DLQ are intentionally visible state
                job.run.error = str(exc)
                if job.run.attempt < self.max_attempts:
                    self.repository.update_import(job.run.id, "failed", attempt=job.run.attempt, error=job.run.error)
                    self.queue.put(job)
                else:
                    job.run.status = "dead_letter"; self.dead_letter.append(job)
                    self.repository.update_import(job.run.id, "dead_letter", attempt=job.run.attempt, error=job.run.error)
            finally: self.queue.task_done()
