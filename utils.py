"""
utils.py

General utilities
"""

import json
import logging
import logging.config
import os
import sys
import time

import pygame

PY2 = sys.version_info[0] < 3

if not PY2:
    # Hack to support tests for strings
    basestring = str  # pylint: disable=invalid-name


def init():
    """Initialize the global config structure"""
    # pylint: disable=global-statement, invalid-name
    global config
    config = get_config("config.json")


def set_config(fname, obj):
    """Write a JSON config file"""
    with open(fname, "wb") as fout:
        json.dump(obj, fout)


def get_config(fname):
    """Load a JSON config file"""
    with open(fname, "rb") as fin:
        return json.load(fin)


def setup_logging(fname):
    """Load logging configuration from JSON file."""
    if os.path.exists(fname):
        cfg = get_config(fname)
        logging.config.dictConfig(cfg)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.error("Missing logging config <%s>", fname)


def lerp(pt1, pt2, ratio):
    """Generic linear interpolation"""
    mixed = [(pt1[i] * ratio + pt2[i] * (1.0 - ratio))
             for i in range(len(pt1))]
    cast = type(pt1)
    final = cast(mixed)
    return final


def color(value):
    """Normalize a color value"""
    if isinstance(value, basestring):
        mycolor = pygame.Color(value)
        value = [mycolor.r, mycolor.g, mycolor.b, mycolor.a]
    return value


def blend(color1, color2, ratio):
    """Blend two colors"""
    color1 = color(color1)
    color2 = color(color2)
    final = lerp(color1, color2, ratio)
    return final


# Events:
EVT_KEYDOWN = pygame.KEYDOWN
EVT_KEYUP = pygame.KEYUP
EVT_MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN
EVT_MOUSEMOTION = pygame.MOUSEMOTION
EVT_VAR_CHANGE = pygame.USEREVENT               # name, value
EVT_POINTS = pygame.USEREVENT + 1               # points
EVT_CAPSULE = pygame.USEREVENT + 2              # position
EVT_EXTRA_LIFE = pygame.USEREVENT + 3           # none
EVT_FIRE = pygame.USEREVENT + 4                 # none
EVT_PADDLEMOVE = pygame.USEREVENT + 5           # delta


class Events:
    """Synchronous event dispatcher"""

    def __init__(self):
        self.clear()

    def register(self, eventtype, handler):
        """Register a handler method for the given event"""
        handlers = self.handlers.setdefault(eventtype, set())
        handlers.add(handler)

    def unregister(self, eventtype, handler):
        """Unregister a handler method for the given event"""
        handlers = self.handlers.setdefault(eventtype, set())
        if handler in handlers:
            handlers.remove(handler)

    def handle(self, event):
        """Handle an incoming event"""
        handlers = self.handlers.get(event.type, set())
        for handler in handlers.copy():
            handler(event)

    def generate(self, event_type, **kwargs):
        """Generate the given event"""
        event = pygame.event.Event(event_type, **kwargs)
        self.handle(event)

    def clear(self):
        """Clear all event handlers"""
        self.handlers = {}


class Timers:
    """Invokes callbacks after a specified delay in frames"""

    def __init__(self):
        self.clear()

    def update(self):
        """Invoke any pending timers"""
        initial_timers = list(self.timers.items())
        for handler, [frames, args, kwargs] in initial_timers:
            frames -= 1

            if frames <= 0:
                self.cancel(handler)
                handler(*args, **kwargs)
            else:
                self.timers[handler] = [frames, args, kwargs]

    def start(self, delay, handler, *args, **kwargs):
        """Start a timer callback with the specified delay and arguments"""
        fps = config["frame_rate"]
        frames = int(delay * fps)
        self.timers[handler] = [frames, args, kwargs]

    def cancel(self, handler):
        """Cancel a timer callback"""
        self.timers.pop(handler, None)

    def clear(self):
        """Clear all pending timer callbacks"""
        self.timers = {}


class Delta:
    """Track time between calls to the millisecond"""

    def __init__(self):
        self.last = time.time()

    def get(self):
        """Get the time in milliseconds since last call"""
        now = time.time()
        delta = now - self.last
        self.last = now
        return delta


class Cache:
    """Cache objects whose creation is expensive.  Replace with lru_cache"""

    def __init__(self, factory):
        self.cache = {}
        self.factory = factory

    def get(self, key):
        """Fetch the item from the cache if present, else create it with the factory"""
        item = self.cache.get(key)
        if item is None:
            item = self.factory(key)
            self.cache[key] = item
            logging.warning("Cache miss: %s", key)
        return item


# Globals
# pylint: disable=invalid-name
config = {}     # initialized in main
events = Events()
timers = Timers()
