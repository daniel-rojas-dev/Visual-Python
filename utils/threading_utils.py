"""
threading_utils.py — Thread-safe utilities for background work.
Avoids UI freezing on 'PC humilde' by offloading heavy tasks to daemon threads.
"""
import threading
import queue


class ThreadPool:
    """Simple thread pool that runs tasks and delivers results to the UI thread."""

    def __init__(self):
        self._result_queue: queue.Queue = queue.Queue()

    def run_in_thread(self, fn, callback=None, error_callback=None):
        """
        Run `fn` in a daemon thread.
        When done, enqueue (callback, result) for the main thread to pick up.
        """
        def _worker():
            try:
                result = fn()
                if callback:
                    self._result_queue.put((callback, result, None))
            except Exception as exc:
                if error_callback:
                    self._result_queue.put((error_callback, None, exc))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def process_results(self, widget, interval_ms=50):
        """
        Call this periodically from the main thread (via widget.after)
        to execute queued callbacks safely on the UI thread.
        """
        try:
            while not self._result_queue.empty():
                cb, result, error = self._result_queue.get_nowait()
                if error is not None:
                    cb(error)
                else:
                    cb(result)
        except queue.Empty:
            pass
        widget.after(interval_ms, self.process_results, widget, interval_ms)


# Global singleton — import and reuse everywhere
thread_pool = ThreadPool()
