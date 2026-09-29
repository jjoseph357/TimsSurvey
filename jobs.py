import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from sites import detect_site


class Job:
    def __init__(self, code, site, automator):
        self.id = str(uuid.uuid4())
        self.code = code
        self.site = site
        self.automator = automator
        self.state = 'queued'  # queued -> running -> done | failed
        self.created = time.time()

    def to_dict(self):
        a = self.automator
        return {
            'id': self.id,
            'code': self.code,
            'site': self.site,
            'state': self.state,
            'status': 'Waiting for a free browser...' if self.state == 'queued' else a.status,
            'progress': a.progress,
            'logs': a.logs,
            'result_code': a.result_code,
            'image': os.path.basename(a.result_image_path) if a.result_image_path else None,
            'code_image': os.path.basename(a.code_image_path) if a.code_image_path else None,
        }


class JobManager:
    """Runs surveys concurrently, at most `max_concurrent` at a time; the rest wait in order."""

    def __init__(self, make_automator, max_concurrent):
        self._make_automator = make_automator
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._jobs = {}
        self._lock = threading.Lock()

    def submit(self, code, on_success=None):
        detected = detect_site(code)
        if not detected:
            raise ValueError(f"Unrecognized code: {code}")
        site, clean = detected
        job = Job(clean, site, self._make_automator(site))
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run, job, on_success)
        return job

    def _run(self, job, on_success):
        job.state = 'running'
        try:
            job.automator.start_survey(job.code, on_success=on_success)
        except Exception as e:
            job.automator.status = f"Error: {e}"
        job.state = 'done' if job.automator.status == 'Completed' else 'failed'

    def get(self, job_id):
        return self._jobs.get(job_id)

    def list(self):
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created)

    def remove(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.state in ('done', 'failed'):
                del self._jobs[job_id]
                return True
            return False
