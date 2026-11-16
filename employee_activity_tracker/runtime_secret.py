import json
import os
from pathlib import Path


def load_runtime_secret():
    path = os.environ.get("CLOCKIN_RUNTIME_SECRET_PATH")
    if not path:
        return
    values = json.loads(Path(path).read_text())
    if not isinstance(values, dict) or not values:
        raise RuntimeError("Invalid Clockin runtime configuration")
    for name, value in values.items():
        if not isinstance(name, str) or not name.isidentifier() or not isinstance(value, str):
            raise RuntimeError("Invalid Clockin runtime configuration entry")
        os.environ[name] = value
