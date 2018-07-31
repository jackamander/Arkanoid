"""
levels.py

Create the JSON for the levels
"""

import json

# Data is the level layout.
# up to 18 rows, 11 columns
# w = white
# p = pink
# c = cyan
# g = green
# r = red
# b = blue
# m = magenta
# o = orange
# S = silver
# G = gold


def create(num, data):
    sprites = [build_bg(num), build_alien(num)]

    bricks = build_bricks(num)
    for row, rowdata in enumerate(data):
        for col, char in enumerate(rowdata):
            if char != " ":
                brick = bricks[char].copy()
                brick["position"] = [16 + 16 * col, 8 + 8 * row]
                sprites.append(brick)

    return {"level%d" % num : sprites}

def write(data, fname):
    with file(fname, "wb") as fout:
        json.dump(data, fout, indent=4)

def build_bg(num):
    bg_index = (num - 1) % 4
    return {
        "name" : "bg",
        "image" : "bg%d" % bg_index,
        "position" : [16, 8],
        "layer" : 0
    }

def build_alien(num):
    alien_index = (num - 1) % 4
    return {
        "name" : "alien",
        "image" : "alien%d_0" % alien_index,
        "hit_sound" : "Alien",
        "animation" : "alien%d" % alien_index,
        "death_animation" : "dead",
        "position" : [1000, 1000],
        "layer" : 30,
        "hits" : 1,
        "points" : 100,
        "groups" : ["aliens"]
    }

def build_bricks(num):
    silver_points = 50 * num
    silver_hits = 2 + (num - 1) / 8

    return {
        "p" : {
            "image" : "pink",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 50,
            "on_death" : "create_capsule"
        },

        "o" : {
            "image" : "orange",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 60,
            "on_death" : "create_capsule"
        },

        "c" : {
            "image" : "cyan",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 70,
            "on_death" : "create_capsule"
        },

        "g" : {
            "image" : "green",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 80,
            "on_death" : "create_capsule"
        },

        "r" : {
            "image" : "red",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 90,
            "on_death" : "create_capsule"
        },

        "b" : {
            "image" : "blue",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 100,
            "on_death" : "create_capsule"
        },

        "m" : {
            "image" : "purple",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 110,
            "on_death" : "create_capsule"
        },

        "w" : {
            "image" : "white",
            "hit_sound" : "Med",
            "hits" : 1,
            "groups" : ["ball", "bricks"],
            "points" : 120,
            "on_death" : "create_capsule"
        },

        "S" : {
            "image" : "silver",
            "hit_sound" : "High",
            "hit_animation" : "silver",
            "hits" : silver_hits,
            "groups" : ["ball", "bricks"],
            "points" : silver_points,
        },

        "G" : {
            "image" : "gold",
            "hit_sound" : "High",
            "hit_animation" : "gold",
            "groups" : ["ball", "bricks"],
        },
    }

def main():
    levels = [
        [           # Level 1
            "",
            "",
            "",
            "",
            "SSSSSSSSSSS",
            "rrrrrrrrrrr",
            "bbbbbbbbbbb",
            "ooooooooooo",
            "ppppppppppp",
            "ggggggggggg",
        ],
        [           # Level 2
            "",
            "",
            "p",
            "pc",
            "pcg",
            "pcgb",
            "pcgbr",
            "pcgbrp",
            "pcgbrpc",
            "pcgbrpcg",
            "pcgbrpcgb",
            "pcgbrpcgbr",
            "SSSSSSSSSSp",
        ],
        [           # Level 3
            "",
            "",
            "",
            "ggggggggggg",
            "",
            "wwwGGGGGGGG",
            "",
            "rrrrrrrrrrr",
            "",
            "GGGGGGGGwww",
            "",
            "ppppppppppp",
            "",
            "bbbGGGGGGGG",
            "",
            "bbbbbbbbbbb",
            "",
            "rrrrrrrrrrr",
        ],
        [           # Level 4
            "",
            "",
            "",
            "",
            " Sogp ogbS ",
            " bgor grSb ",
            " gpro bSrg ",
            " orpg Sbgo ",
            " rogb ogpr ",
            " rgrS gorp ",
            " gbSr prog ",
            " oSbg rpgo ",
            " Sogp ogbS ",
            " bgor grSb ",
            " gpro bSrg ",
            " orpg Sbgo ",
            " rogb ogpr ",
            " pgoS gorp ",
        ],
        [           # Level 5
            "",
            "",
            "   o   o   ",
            "    o o    ",
            "    o o    ",
            "   SSSSS   ",
            "   SSSSS   ",
            "  SSrSrSS  ",
            "  SSrSrSS  ",
            " SSSSSSSSS ",
            " SSSSSSSSS ",
            " S SSSSS S ",
            " S S   S S ",
            " S S   S S ",
            "    S S    ",
            "    S S    ",
        ],
        [           # Level 6
            "",
            "",
            "",
            "b r g g r b",
            "b r g g r b",
            "b r g g r b",
            "b GpGpGpg b",
            "b r g g r b",
            "b r g g r b",
            "b r g g r b",
            "b r g g r b",
            "b r g g r b",
            "p G G G G p",
            "b r g g r b",
        ],
        [           # Level 7
            "",
            "",
            "",
            "",
            "    ocb    ",
            "   ogbco   ",
            "   cbgop   ",
            "  gbcogrp  ",
            "  bgoprgo  ",
            "  cogrpog  ",
            "  oprgocb  ",
            "  grpogbc  ",
            "  rgocbgo  ",
            "   ogbco   ",
            "   cbgop   ",
            "    cog    ",
        ],
        [           # Level 8
            "",
            "",
            "",
            " G  G G  G ",
            " GG     GG ",
            "     p     ",
            "    GgG    ",
            "  G  o  G  ",
            "     b     ",
            "  G  r  G  ",
            "    GgG    ",
            "     o     ",
            " GG     GG ",
            " G  G G  G ",
        ],
        [           # Level 9
            "",
            "",
            " G G   G G ",
            " GgG   GgG ",
            " GbG   GbG ",
            " GGG   GGG ",
            "           ",
            "   pbbbo   ",
            "   pgcgo   ",
            "   pcgco   ",
            "   pgcgo   ",
            "   pcgco   ",
            "   pbbbo   ",
        ],
        [           # Level 10
            " G         ",
            "           ",
            " G         ",
            " G         ",
            " G    b    ",
            " G   bcb   ",
            " G  bcbcb  ",
            " G bcbSbcb ",
            " G  bcbcb  ",
            " G   bcb   ",
            " G    b    ",
            " G         ",
            " G         ",
            " G         ",
            " G         ",
            " GGGGGGGGGG",
        ],
        [           # Level 11
            "           ",
            "           ",
            "           ",
            "           ",
            " SSSSSSSSS ",
            " S       S ",
            " S SSSSS S ",
            " S S   S S ",
            " S S S S S ",
            " S S   S S ",
            " S SSSSS S ",
            " S       S ",
            " SSSSSSSSS ",
        ],
        [           # Level 12
            "           ",
            "           ",
            "GGGGGGGGGGG",
            "    G   Gp ",
            " Gg G   G  ",
            " G  G G G  ",
            " G  G G G  ",
            " G  GgG G  ",
            " G pG GbG  ",
            " G  GrG G  ",
            " G  G G G  ",
            " G  G G G  ",
            " Gb   G    ",
            " G    G   p",
            " GGGGGGGGGG",
        ],
        [           # Level 13
            "           ",
            "           ",
            "           ",
            "           ",
            " oo www oo ",
            " ww ooo ww ",
            " bb rrr bb ",
            " mm ggg mm ",
            " gg mmm gg ",
            " rr bbb rr ",
            " oo www oo ",
            " ww ooo ww ",
        ],
        [           # Level 14
            "           ",
            "           ",
            "           ",
            "rSSSSSSSSSr",
            "G         G",
            "bbbbbbbbbbb",
            "           ",
            "pSSSSSSSSSp",
            "G         G",
            "bbbbbbbbbbb",
            "           ",
            "bSSSSSSSSSb",
            "G         G",
            "rrrrrrrrrrr",
            "           ",
            "rrrrrrrrrrr",
            "G         G",
        ],
        [           # Level 15
            "           ",
            "           ",
            "           ",
            "cSScccccSSc",
            "cSoScccSgSc",
            "cSooSSSggSc",
            "cSoooSgggSc",
            "cSoooSgggSc",
            "cSoooSgggSc",
            "cSoooSgggSc",
            "cSoooSgggSc",
            "cSoooSgggSc",
            "ccSooSggScc",
            "cccSoSgSccc",
            "ccccSSScccc",
        ],
    ]

    results = {}
    for index, data in enumerate(levels):
        level = create(index + 1, data)
        results.update(level)

    write(results, "levels.txt")

if __name__ == "__main__":
    main()
