"""Shared opt-out for the gallery builders.

Drop an empty file named `.nogallery` into a target directory
(targets/<category>/<object>/.nogallery) and every builder skips that object:
no card on the all-targets page, no Messier or Caldwell tile. The data stays
where it is; this only hides it from the published site. Remove the marker
(or add a properly processed image) to publish the object.
"""
from pathlib import Path

MARKER = '.nogallery'


def is_excluded(path):
    """True when `path` (a target dir or any file under one) carries the marker."""
    parts = Path(path).parts
    # targets/<category>/<object>/...
    if len(parts) < 3:
        return False
    return (Path(*parts[:3]) / MARKER).exists()
