import json
import time
from logging import getLogger
from pathlib import Path
from typing import Any
from typing import Tuple

import yaml

LOGGER = getLogger(__name__)


def wait_for(
    func, delay: float = 2.0, num_sec: float = 10.0, ignore_falsy: bool = False
) -> Tuple[Any, Any, int]:
    """Wait for success of `func` for `num_sec`."""
    end_time = time.time() + num_sec

    tries = 0

    while time.time() < end_time:
        response = None
        err = None
        tries += 1

        try:
            response = func()
        # pylint: disable=broad-except
        except Exception as exp:
            err = exp
            LOGGER.warning(f"{tries} tries fail, Handling exception: {err}")
            continue

        if response or ignore_falsy:
            return response, err, tries

        time.sleep(delay)

    return response, err, tries


def load_file(path):
    """Load a .json/.yml/.yaml file. (Logic taken from bonfire)"""
    if not isinstance(path, Path):
        path = Path(path)

    if not path.exists():
        raise ValueError(f"Path '{path}' is not a file or does not exist.")

    with open(path, "rb") as f:
        if path.suffix in [".yaml", ".yml"]:
            content = yaml.safe_load(f)
        elif path.suffix == ".json":
            content = json.load(f)
        else:
            raise ValueError(f"File '{path}' must be a YAML or JSON file.")

    if not content:
        raise ValueError(f"File '{path}' is empty!")

    return content


def merge_dicts(dict_a, dict_b):
    """Merge dict_b into dict_a."""
    if not (isinstance(dict_a, dict) and isinstance(dict_b, dict)):
        return dict_a

    mergeable = (list, set, tuple)
    for key, value in dict_b.items():
        if key in dict_a and isinstance(value, mergeable) and isinstance(dict_a[key], mergeable):
            new_list = set(dict_a[key]).union(value)
            dict_a[key] = sorted(new_list)
        elif key not in dict_a or not isinstance(value, dict):
            dict_a[key] = value
        else:
            merge_dicts(dict_a[key], value)

    return dict_a
