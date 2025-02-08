"""
utils.py

General utilities
"""

import collections
import enum
import json
import logging
import logging.config
import pathlib
from random import Random
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

    global random
    random.seed(config["seed"])


def set_config(fname, obj):
    """Write a JSON config file"""
    with open(fname, "wb") as fout:
        json.dump(obj, fout)


def get_config(fname):
    """Load a JSON config file"""
    fpath = pathlib.Path("cfg") / fname
    with fpath.open("rb") as fin:
        return json.load(fin)


def setup_logging(fname):
    """Load logging configuration from JSON file."""
    try:
        pathlib.Path("logs").mkdir(exist_ok=True)
        cfg = get_config(fname)
        logging.config.dictConfig(cfg)
    except FileNotFoundError:
        logging.basicConfig(level=logging.INFO)
        logging.error("Missing logging config <%s>", fname)


class StreamToFunc:
    """Stream that directs to logging functions"""

    def __init__(self, writefunc, prefix):
        self.writefunc = writefunc
        self.prefix = prefix
        self.buffer = ""

    def write(self, message):
        """Called by writes to stream"""
        self.buffer += message
        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            self.writefunc(self.prefix + line)

    def flush(self):
        """Flush function to fulfill stream API"""
        pass    #pylint:disable=unnecessary-pass

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
class Event(enum.IntEnum):
    """Game events for use with the Events class below"""
    QUIT = pygame.QUIT                          # none
    ACTIVEEVENT = pygame.ACTIVEEVENT            # gain, state
    KEYDOWN = pygame.KEYDOWN                    # unicode, key, mod
    KEYUP = pygame.KEYUP                        # key, mod
    MOUSEMOTION = pygame.MOUSEMOTION            # pos, rel, buttons
    MOUSEBUTTONUP = pygame.MOUSEBUTTONUP        # pos, button
    MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN    # pos, button
    JOYAXISMOTION = pygame.JOYAXISMOTION        # joy, axis, value
    JOYBALLMOTION = pygame.JOYBALLMOTION        # joy, ball, rel
    JOYHATMOTION = pygame.JOYHATMOTION          # joy, hat, value
    JOYBUTTONUP = pygame.JOYBUTTONUP            # joy, button
    JOYBUTTONDOWN = pygame.JOYBUTTONDOWN        # joy, button
    VIDEORESIZE = pygame.VIDEORESIZE            # size, w, h
    VIDEOEXPOSE = pygame.VIDEOEXPOSE            # none
    VAR_CHANGE = pygame.USEREVENT               # name, value
    POINTS = pygame.USEREVENT + 1               # points
    CAPSULE = pygame.USEREVENT + 2              # position
    EXTRA_LIFE = pygame.USEREVENT + 3           # none
    FIRE = pygame.USEREVENT + 4                 # none
    PADDLEMOVE = pygame.USEREVENT + 5           # delta
    VAR_REQUEST = pygame.USEREVENT + 6          # name


class Events:
    """Synchronous event dispatcher"""

    def __init__(self):
        self.handlers = collections.defaultdict(set)

    def register(self, eventtype, handler):
        """Register a handler method for the given event"""
        handlers = self.handlers[eventtype]
        handlers.add(handler)

    def unregister(self, eventtype, handler):
        """Unregister a handler method for the given event"""
        handlers = self.handlers[eventtype]
        handlers.discard(handler)

    def handle(self, event):
        """Handle an incoming event"""
        logging.debug("%s", pygame.event.event_name(event.type))
        handlers = self.handlers[event.type]
        for handler in handlers.copy():
            handler(event)

    def generate(self, event_type, **kwargs):
        """Generate the given event"""
        event = pygame.event.Event(event_type, **kwargs)
        self.handle(event)


class Timers:
    """Invokes callbacks after a specified delay in frames"""

    def __init__(self):
        self.timers = {}

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


# Globals
# pylint: disable=invalid-name
config = {}     # initialized in main
events = Events()
timers = Timers()
random = Random()
