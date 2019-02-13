"""
levels.py

Create the JSON for the levels.

Data is the level layout.
up to 18 rows, 11 columns
w = white
p = pink
c = cyan
g = green
r = red
b = blue
m = magenta
o = orange
S = silver
G = gold
"""

import json
import re


def create_sprites(num, data):
    "Create all the sprite data for a level"
    sprites = [build_bg(num), build_alien(num)]

    bricks = build_bricks(num)
    for row, rowdata in enumerate(data):
        for col, char in enumerate(rowdata):
            if char != " ":
                brick = bricks[char].copy()
                brick["position"] = [16 + 16 * col, 8 + 8 * row]
                sprites.append(brick)

    return sprites


def build_bg(num):
    bg_index = (num - 1) % 4
    bg = {
        "name": "bg",
        "image": "bg%d" % bg_index,
        "position": [16, 8],
        "layer": 0
    }
    return bg


def build_alien(num):
    alien_index = (num - 1) % 4
    alien = {
        "name": "alien",
        "image": "alien%d_0" % alien_index,
        "hit_sound": "Alien",
        "animation": "alien%d" % alien_index,
        "death_animation": "dead",
        "position": [1000, 1000],
        "layer": 30,
        "hits": 1,
        "points": 100,
        "groups": ["aliens"]
    }
    return alien


def build_bricks(num):
    silver_points = 50 * num
    silver_hits = 2 + (num - 1) // 8

    bricks = {
        "p": {
            "image": "pink",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 50,
            "on_death": "create_capsule"
        },

        "o": {
            "image": "orange",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 60,
            "on_death": "create_capsule"
        },

        "c": {
            "image": "cyan",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 70,
            "on_death": "create_capsule"
        },

        "g": {
            "image": "green",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 80,
            "on_death": "create_capsule"
        },

        "r": {
            "image": "red",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 90,
            "on_death": "create_capsule"
        },

        "b": {
            "image": "blue",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 100,
            "on_death": "create_capsule"
        },

        "m": {
            "image": "purple",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 110,
            "on_death": "create_capsule"
        },

        "w": {
            "image": "white",
            "hit_sound": "Med",
            "hits": 1,
            "groups": ["ball", "bricks"],
            "points": 120,
            "on_death": "create_capsule"
        },

        "S": {
            "image": "silver",
            "hit_sound": "High",
            "hit_animation": "silver",
            "hits": silver_hits,
            "groups": ["ball", "bricks"],
            "points": silver_points,
        },

        "G": {
            "image": "gold",
            "hit_sound": "High",
            "hit_animation": "gold",
            "groups": ["ball", "bricks"],
        },
    }
    return bricks


def parse_num(key):
    "Parse the level number from the JSON key"
    mobj = re.match(r"level(\d+)", key)
    assert mobj != None, "Bad level key %s" % key
    return int(mobj.group(1))


def create_scene_configs(levels):
    "Create the scene configuration objects from the levels JSON"
    configs = {}

    for key, data in levels.items():
        num = parse_num(key)
        configs[key] = create_sprites(num, data)

    return configs
