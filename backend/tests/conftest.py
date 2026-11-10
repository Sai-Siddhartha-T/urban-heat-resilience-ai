"""Tests configuration: isolated temporary DB, pre-seeded models, instant startup, and Windows IOCP patch."""

import atexit
import os
from pathlib import Path
import shutil
import sys
import tempfile
import pytest

os.environ["TESTING"] = "1"

# ---------------------------------------------------------------------------
# Windows Sandbox IOCP Proactor Patch (prevents socketpair connect hang)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import _overlapped
    import signal
    import asyncio.windows_events as _we
    import asyncio.proactor_events as _pe

    _orig_set_wakeup_fd = signal.set_wakeup_fd

    def _safe_set_wakeup_fd(fd, *args, **kwargs):
        try:
            return _orig_set_wakeup_fd(fd, *args, **kwargs)
        except OSError:
            return -1

    signal.set_wakeup_fd = _safe_set_wakeup_fd

    class _DummySocket:
        def fileno(self):
            return -1

        def setblocking(self, flag):
            pass

        def send(self, data):
            return len(data)

        def close(self):
            pass

    def _make_self_pipe(self):
        self._ssock = _DummySocket()
        self._csock = _DummySocket()
        self._internal_fds += 1

    def _close_self_pipe(self):
        self._self_reading_future = None
        self._ssock = None
        self._csock = None
        self._internal_fds -= 1

    def _loop_self_reading(self, f=None):
        pass

    def _write_to_self(self):
        try:
            _overlapped.PostQueuedCompletionStatus(self._proactor._iocp, 0, 0, 0)
        except Exception:
            pass

    _pe.BaseProactorEventLoop._make_self_pipe = _make_self_pipe
    _pe.BaseProactorEventLoop._close_self_pipe = _close_self_pipe
    _pe.BaseProactorEventLoop._loop_self_reading = _loop_self_reading
    _pe.BaseProactorEventLoop._write_to_self = _write_to_self

    _orig_poll = _we.IocpProactor._poll

    def _safe_poll(self, timeout=None):
        try:
            return _orig_poll(self, timeout)
        except OSError:
            return

    _we.IocpProactor._poll = _safe_poll

_temp = tempfile.TemporaryDirectory(prefix="heatwise-tests-")
_temp_path = Path(_temp.name)

# Database & model isolation
os.environ["DATABASE_URL"] = "sqlite:///" + str(_temp_path / "tests.db")
test_models_dir = _temp_path / "models"
test_models_dir.mkdir(parents=True, exist_ok=True)
os.environ["MODEL_DIR"] = str(test_models_dir)

# Ensure Matplotlib uses a writable temp directory to avoid multiprocessing warnings
mpl_dir = _temp_path / "mpl"
mpl_dir.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_dir)

# Fast startup flag enables instant boot (<50ms) across all TestClient fixtures
os.environ["FAST_STARTUP"] = "1"
os.environ["PREWARM_STATE"] = "0"
# Tests that exercise the legacy analytical workflow opt into Demo Mode
# explicitly; production startup never enables this flag by default.
os.environ["HEATWISE_DEMO_MODE"] = "1"
os.environ["ML_JOBS"] = "1"
os.environ["ML_N_JOBS"] = "1"
os.environ["API_TOKEN"] = ""

# Pre-seed pre-trained models into temporary test directory if available
src_models = Path(__file__).resolve().parents[1] / "models"
if src_models.exists():
    for f in src_models.glob("*.joblib"):
        shutil.copy2(f, test_models_dir / f.name)

atexit.register(_temp.cleanup)


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Clear in-memory rate limiter queue before and after each test."""
    try:
        from app.main import RATE
        RATE.clear()
    except Exception:
        pass
    yield
    try:
        from app.main import RATE
        RATE.clear()
    except Exception:
        pass
