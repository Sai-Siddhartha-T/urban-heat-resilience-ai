"""Tests must never populate the demonstration database with mocked remote data."""

import os, tempfile, atexit
from pathlib import Path

_temp = tempfile.TemporaryDirectory(prefix="heatwise-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_temp.name) / "tests.db")
os.environ["MODEL_DIR"] = str(Path(_temp.name) / "models")
os.environ["MPLCONFIGDIR"] = str(Path(_temp.name) / "mpl")
os.environ["API_TOKEN"] = ""
atexit.register(_temp.cleanup)
