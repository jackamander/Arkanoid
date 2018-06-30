"""
utils.py

General utilities
"""

import json
import logging
import math
import os

import pygame

def set_config(fname, obj):
    """Write a JSON config file"""
    with file(fname, "wb") as fout:
        json.dump(obj, fout)

def get_config(fname):
    """Load a JSON config file"""
    with file(fname, "rb") as fin:
        return json.load(fin)

def setup_logging(fname):
    """Load logging configuration from JSON file."""
    if os.path.exists(fname):
        config = get_config(fname)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warn("Missing logging config <%s>", fname)

def lerp(pt1, pt2, ratio):
    """Generic linear interpolation"""
    mixed = [(pt1[i] * ratio + pt2[i] * (1.0 - ratio)) for i in range(len(pt1))]
    cast = type(pt1)
    final = cast(mixed)
    return final

def color(value):
    """Normalize a color value"""
    if isinstance(value, str) or isinstance(value, unicode):
        mycolor = pygame.Color(value)
        value = [mycolor.r, mycolor.g, mycolor.b, mycolor.a]
    return value

def blend(color1, color2, ratio):
    """Blend two colors"""
    color1 = color(color1)
    color2 = color(color2)
    final = lerp(color1, color2, ratio)
    return final

# Global config file - initialized in main
config = None
