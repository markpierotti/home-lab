"""Installed gateway lifecycle adapter; no mutation of Hermes internals."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.hermes/scripts'))
from slim_incidents import lifecycle


def handle(event_type, context):
    lifecycle(event_type, context)
