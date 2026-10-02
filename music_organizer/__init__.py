#!/usr/bin/env python3
"""Music Organizer - Clean, organize, and rename music files."""

__version__ = "2.0.0"
__author__ = "Music Organizer Contributors"

from . import config
from . import core
from . import analysis
from . import logging

__all__ = ['config', 'core', 'analysis', 'logging']
