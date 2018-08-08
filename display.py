"""
display.py

Display functionality
"""
import logging
import math
import os
import random

import pygame

import audio
import utils

class Window:
    def __init__(self):
        world_size = utils.config['world_size']
        screen_size = utils.config['screen_size']

        flags = 0
        if utils.config['full_screen']:
            flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF

        self.main = pygame.display.set_mode(screen_size, flags)
        self.screen = pygame.Surface(world_size)

        logging.info("Driver: %s", pygame.display.get_driver())
        logging.info("Display Info:\n    %s", pygame.display.Info())

        pygame.display.set_caption(utils.config["title"])

    def flip(self):
        pygame.transform.scale(self.screen, self.main.get_size(), self.main)
        pygame.display.flip()

    def clear(self):
        self.screen.fill(utils.color(utils.config["bg_color"]))

def grab_mouse():
    pygame.mouse.set_visible(0)
    pygame.event.set_grab(1)

def release_mouse():
    pygame.mouse.set_visible(1)
    pygame.event.set_grab(0)

def _find_char_offset(char, characters):
    for row, data in enumerate(characters):
        col = data.find(char)
        if col > -1:
            return [col, row]

    raise ValueError("Unsupported Character: %s" % char)

def draw_text(text, font):
    config = utils.config["fonts"][font]
    filename = config["filename"]
    size = config["size"]
    characters = config["characters"]

    text_split = text.split('\n')
    rows = len(text_split)
    cols = max(map(len, text_split))

    surf = pygame.Surface([size[0] * cols, size[1] * rows], pygame.SRCALPHA).convert_alpha()
    image = _load_image(filename)
    for row, line in enumerate(text_split):
        for col, char in enumerate(line):
            offset = _find_char_offset(char, characters)
            offset = [offset[i] * size[i] for i in range(2)]

            surf.blit(image, [col * size[0], row * size[1]], pygame.Rect(offset, size), pygame.BLEND_RGBA_MAX)

    return surf

_image_cache = {}

def _load_image(fname, rect=None, scaled=[]):
    image = _image_cache.get(fname)
    if image is None:
        image = pygame.image.load(fname)
        image = image.convert_alpha()
        _image_cache[fname] = image

    if rect:
        image = image.subsurface(rect)

    if scaled:
        image = pygame.transform.smoothscale(image, scaled)

    return image

def get_image(name):
    cfg = utils.config["images"][name]

    fname = cfg["filename"]
    size = cfg["size"]
    offset = cfg["offset"]
    scaled = cfg.get("scaled")

    rect = pygame.Rect(offset, size)

    image = _load_image(fname, rect, scaled)

    return image

class Action:
    def then(self, next):
        return Series([self, next])

    def plus(self, action):
        return Parallel([self, action])

    def update(self):
        return True

class Series(Action):
    def __init__(self, actions):
        self.actions = list(actions)
        self.action = self.actions.pop(0)

    def update(self, sprite):
        if self.action:
            done = self.action.update(sprite)
            if done:
                self.action = None
                if self.actions:
                    self.action = self.actions.pop(0)

        return self.action is None

class Parallel(Action):
    def __init__(self, actions):
        self.actions = list(actions)

    def update(self, sprite):
        self.actions = filter(lambda action: not action.update(sprite), self.actions)
        done = len(self.actions) == 0
        return done

class MouseMove(Action):
    def __init__(self, sprite, region, sensitivity):
        self.sprite = sprite
        self.rect = region.copy()
        self.sensitivity = sensitivity

        utils.events.register(utils.EVT_MOUSEMOTION, self.on_mousemove)

    def on_mousemove(self, event):
        delta = [self.sensitivity[i] * event.rel[i] for i in range(2)]
        self.sprite.move(delta)
        self.sprite.rect.clamp_ip(self.rect)

    def update(self, sprite):
        return False

class Move(Action):
    def __init__(self, delta):
        self.delta = delta
        self.total = [0,0]

    def update(self, sprite):
        total = [t + d for t,d in zip(self.total, self.delta)]
        move = [int(i) for i in total]
        self.total = [t-m for t,m in zip(total, move)]
        sprite.move(move)

class MoveLimited(Move):
    def __init__(self, delta, frames):
        Move.__init__(self, delta)
        self.frames = frames

    def update(self, sprite):
        Move.update(self, sprite)

        if self.frames > 0:
            self.frames -= 1

        return self.frames == 0

class Follow(Action):
    def __init__(self, target):
        self.target = target
        self.last = target.get_pos()

    def update(self, sprite):
        pos = self.target.get_pos()
        if pos != self.last:
            delta = [pos[0] - self.last[0], pos[1] - self.last[1]]
            sprite.move(delta)
            self.last = pos

class Blink(Action):
    def __init__(self, rate):
        # Convert rate from seconds to frames per half cycle
        fps = utils.config["frame_rate"]
        self.rate = int(rate * fps) / 2
        self.frames = 0

    def update(self, sprite):
        self.frames += 1

        if self.frames == self.rate:
            sprite.visible ^= 1
            self.frames = 0

class Animate(Action):
    def __init__(self, name, align="center"):
        cfg = utils.config["animations"][name]
        self.images = [get_image(name) for name in cfg["images"]]
        self.speed = cfg["speed"]
        self.loop = cfg.get("loop")
        self.align = align
        self.frame = 0
        self.count = 0

    def update(self, sprite):
        if self.frame < len(self.images):
            if self.count == 0:
                image = self.images[self.frame]
                sprite.set_image(image, self.align)

            self.count += 1
            if self.count >= self.speed:
                self.frame += 1
                self.count = 0

        if self.frame >= len(self.images):
            if self.loop:
                self.frame = 0
            else:
                return True

class Die(Action):
    def update(self, sprite):
        sprite.kill()
        return True

class PlaySound(Action):
    def __init__(self, sound):
        self.sound = audio.play_sound(sound)

    def update(self, sprite):
        return self.sound is None or not self.sound.get_busy()

class FireEvent(Action):
    def __init__(self, event, **kwargs):
        self.event = event
        self.kwargs = kwargs

    def update(self, sprite):
        if self.event:
            utils.events.generate(self.event, **self.kwargs)
            self.event = None
        return True

class Callback(Action):
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def update(self, sprite):
        if self.callback:
            self.callback(*self.args, **self.kwargs)
            self.callback = None
        return True

class UpdateVar(Action):
    def __init__(self, name, font="white", fmt="%s"):
        self.name = name
        self.font = font
        self.fmt = fmt
        self.text = ""
        self.dirty = False

        utils.events.register(utils.EVT_VAR_CHANGE, self.on_var_change)

    def on_var_change(self, event):
        if event.name == self.name:
            self.dirty = True
            self.text = self.fmt % event.value

    def update(self, sprite):
        if self.dirty:
            self.dirty = False
            image = draw_text(self.text, self.font)
            sprite.set_image(image)

class Delay(Action):
    def __init__(self, delay):
        fps = utils.config["frame_rate"]
        self.frames = int(delay * fps)

    def update(self, sprite):
        if self.frames > 0:
            self.frames -= 1
        return self.frames == 0

class Spawn(Action):
    def __init__(self, name, scene):
        self.clone = scene.names[name]
        self.scene = scene

    def update(self, sprite):
        clone = self.clone.clone()

        clone.rect.center = sprite.rect.center
        clone.rect.bottom = sprite.rect.top

        action = MoveLimited([0,0.25], 96).then(AlienEscape(self.scene))

        animation = clone.cfg["animation"]
        if animation:
            action = action.plus(Animate(animation))

        clone.set_action(action)
        self.scene.groups["all"].add(clone)
        self.scene.groups["ball"].add(clone)
        self.scene.groups["paddle"].add(clone)
        self.scene.groups["aliens"].add(clone)

        return True

class AlienEscape(Move):
    def __init__(self, scene):
        self.scene = scene
        self.states = [("down", "left"), ("left", "up"),  ("down", "right"), ("right", "up")]
        self.index = 0
        self.tests = {
            "up" : [0, -1],
            "down" : [0, 1],
            "left" : [-1, 0],
            "right" : [1, 0],
        }
        self.speed = 0.25

        Move.__init__(self, [0,0])

    def attempt(self, sprite, direction):
        success = False
        delta = self.tests[direction]

        # Temporarily move in the requested direction
        sprite.move(delta)

        # if it only collides with itself, we're good
        others = pygame.sprite.spritecollide(sprite, self.scene.groups["ball"], False)
        if len(others) == 1:
            success = True

        # Move back
        sprite.move([-i for i in delta])

        return success

    def move(self, sprite):
        initial = self.index
        while True:
            first, second = self.states[self.index]

            # Try the preferred directions first
            for direction in [first, second]:
                if self.attempt(sprite, direction):
                    self.delta = [i * self.speed for i in self.tests[direction]]
                    Move.update(self, sprite)
                    return

            # If both fail, roll to the next state
            self.index = (self.index + 1) % len(self.states)

            # Do nothing if we try all the options and can't find an out
            if self.index == initial:
                break

    def update(self, sprite):
        self.move(sprite)

        # check whether to change behavior
        rect = pygame.Rect(0,0,0,0)
        for brick in self.scene.groups["bricks"].sprites():
            rect.union_ip(brick.rect)

        if sprite.rect.top > rect.bottom:
            sprite.set_action(AlienDescend(self.scene))


class AlienDescend(MoveLimited):
    def __init__(self, scene):
        MoveLimited.__init__(self, [0, 0.25], 60)
        self.scene = scene

    def update(self, sprite):
        if MoveLimited.update(self, sprite):
            actions = [AlienDescend(self.scene)]
            playspace = self.scene.names["bg"].rect

            if sprite.rect.right < playspace.right - 32:
                actions += [AlienJuke(self.scene, 1)]

            if sprite.rect.right < playspace.right - 40:
                actions += [AlienCircle(self.scene, 1)]

            if sprite.rect.left > playspace.left + 32:
                actions += [AlienJuke(self.scene, -1)]

            if sprite.rect.left > playspace.left + 40:
                actions += [AlienCircle(self.scene, -1)]

            sprite.set_action(random.choice(actions))

class AlienJuke(MoveLimited):
    def __init__(self, scene, xdir):
        self.scene = scene
        self.init()
        self.deltas = [[x * xdir, y] for x,y in self.deltas]
        self.index = 0
        self.set()

    def init(self):
        self.deltas = [[0.25, 0.5], [0.5, 0.5], [0.5, 0.25], [0.25, 0.5]]
        self.frame_counts = [10, 30, 10, 10]

    def set(self):
        delta = self.deltas[self.index]
        frames = self.frame_counts[self.index]
        MoveLimited.__init__(self, delta, frames)

    def update(self, sprite):
        if MoveLimited.update(self, sprite):
            self.index += 1

            if self.index < len(self.deltas):
                self.set()
            else:
                sprite.set_action(AlienDescend(self.scene))

class AlienCircle(AlienJuke):
    def init(self):
        self.deltas = [[0.25, 0.5], [0.5, 0.5], [0.5, 0.25], [0.5, -0.25], [0.5, -0.5], [0.25, -0.5], [-0.25, -0.5], [-0.5, -0.5], [-0.5, -0.25], [-0.5, 0.25], [-0.5, 0.5], [-0.25, 0.5]]
        self.frame_counts = [10, 30, 10, 10, 30, 10, 10, 30, 10, 10, 30, 10]

class InletMgr(Action):
    def __init__(self, scene, inlet):
        self.max_delay = inlet.cfg["max_delay"] * utils.config["frame_rate"]
        self.max_aliens = inlet.cfg["max_aliens"]
        self.scene = scene
        self._randomize()

    def _randomize(self):
        self.frames = random.randrange(self.max_delay)

    def update(self, sprite):
        if self.frames > 0:
            self.frames -= 1
        else:
            if len(self.scene.groups["aliens"].sprites()) < self.max_aliens:
                sprite.set_action(Animate("inlet_open").then(Spawn("alien", self.scene).then(Delay(1.0).then(Animate("inlet_close").then(InletMgr(self.scene, sprite))))))
            self._randomize()

class DohMgr(Action):
    def __init__(self, scene, sprite):
        self.scene = scene
        self.set_state(self.state_open, 1)
        self.set_closed(sprite)

    def delay(self, delay):
        self.frames = delay * utils.config["frame_rate"]

    def update(self, sprite):
        if self.frames > 0:
            self.frames -= 1
        else:
            self.state(sprite)

    def set_open(self, sprite):
        sprite.set_image(get_image("doh_open"))
        sprite.cfg["hit_animation"] = "doh_hit_open"

    def set_closed(self, sprite):
        sprite.set_image(get_image("doh"))
        sprite.cfg["hit_animation"] = "doh_hit"

    def set_state(self, handler, delay):
        self.state = handler
        self.delay(delay)

    def fire(self, sprite):
        shot = self.scene.names["doh_shot"].clone()

        shot.rect.center = sprite.rect.center

        start = shot.rect.center
        target = self.scene.names["paddle"].rect.center

        delta = [target[i] - start[i] for i in range(2)]
        magnitude = math.sqrt(delta[0]**2 + delta[1]**2)
        speed = 3
        delta = [speed * value / magnitude for value in delta]

        action = Move(delta)

        animation = shot.cfg["animation"]
        if animation:
            action = action.plus(Animate(animation))

        shot.set_action(action)
        self.scene.groups["all"].add(shot)
        self.scene.groups["paddle"].add(shot)

    def state_open(self, sprite):
        self.set_open(sprite)
        self.set_state(self.state_fire1, 0.0)

    def state_fire1(self, sprite):
        self.fire(sprite)
        self.set_state(self.state_fire2, 0.5)

    def state_fire2(self, sprite):
        self.fire(sprite)
        self.set_state(self.state_fire3, 0.5)

    def state_fire3(self, sprite):
        self.fire(sprite)
        self.set_state(self.state_close, 0.0)

    def state_close(self, sprite):
        self.set_closed(sprite)
        self.set_state(self.state_open, 4)

class Sprite(pygame.sprite.DirtySprite):
    def __init__(self, image, cfg={}):
        pygame.sprite.DirtySprite.__init__(self)

        self.image = image
        self.rect = image.get_rect()
        self.last = self.rect
        self.dirty = 2
        self.blendmode = 0
        self.source_rect = None
        self.visible = 1

        self._layer = cfg.get("layer", 10)

        self.action = None

        self.cfg = cfg

    def clone(self):
        return Sprite(self.image, self.cfg.copy())

    def get_pos(self):
        return self.rect.topleft

    def set_pos(self, pos):
        self.rect.x = pos[0]
        self.rect.y = pos[1]

    def move(self, delta):
        self.rect.x += delta[0]
        self.rect.y += delta[1]

    def set_action(self, action=None):
        self.action = action

    def update(self):
        self.last = self.rect.copy()
        if self.action:
            done = self.action.update(self)
            if done:
                self.action = None

    def set_image(self, image, align="center"):
        old_rect = self.rect.copy()
        self.image = image
        self.rect.size = image.get_size()
        setattr(self.rect, align, getattr(old_rect, align))

    def hit(self, scene):
        sound = self.cfg.get("hit_sound")
        if sound:
            audio.play_sound(sound)

        animation = self.cfg.get("hit_animation")
        if animation:
            action = Animate(animation)
            if self.action:
                action = self.action.plus(action)
            self.set_action(action)

        hit_points = self.cfg.get("hit_points")
        if hit_points:
            utils.events.generate(utils.EVT_POINTS, points=hit_points)

        hits = self.cfg.get("hits")
        if hits:
            hits -= 1
            self.cfg["hits"] = hits
            if hits == 0:
                self.kill()

                death_animation = self.cfg.get("death_animation")
                if death_animation:
                    align = self.cfg.get("death_animation_align", "center")
                    self.set_action(Animate(death_animation, align).then(Die()))
                    scene.groups["all"].add(self)

                death_action = self.cfg.get("on_death")
                if death_action == "create_capsule":
                    utils.events.generate(utils.EVT_CAPSULE, position=self.get_pos())

                points = self.cfg.get("points", 0)
                if points:
                    utils.events.generate(utils.EVT_POINTS, points=points)

# Scene requirements:
# - named Sprites for specific processing - paddle, ball, bg, etc
# - multiple groups for things like collision handling and ball tracking
# - single group for rendering everything
# - share definitions for block reuse
# - control persistence - some need to be reinstantiated, others need persistence
class Scene:
    Group = pygame.sprite.LayeredDirty
    def __init__(self, names, var_dict={}):
        self.groups = {}
        self.names = {}

        for name in names:
            sprites = utils.config["scenes"][name]

            for cfg in sprites:
                cfg = cfg.copy()

                action = None

                key = cfg.pop("text", "")
                if key:
                    font = cfg.pop("font", "white")
                    image = draw_text(key, font)

                key = cfg.pop("var", "")
                if key:
                    fmt = cfg.pop("fmt", "%s")
                    text = fmt % var_dict[key]
                    font = cfg.pop("font", "white")
                    image = draw_text(text, font)
                    action = UpdateVar(key, font, fmt)

                key = cfg.pop("image", "")
                if key:
                    image = get_image(key)

                position = cfg.pop("position", [0,0])

                group_names = cfg.pop("groups", [])

                sprite = Sprite(image, cfg)
                sprite.set_pos(position)
                sprite.set_action(action)

                for group_name in group_names + ["all"]:
                    group = self.groups.setdefault(group_name, Scene.Group())
                    group.add(sprite)

                sprite_name = cfg.get("name")
                if sprite_name:
                    self.names[sprite_name] = sprite

    def merge(self, scene):
        for key, source in scene.groups.items():
            dest = self.groups.setdefault(key, Scene.Group())
            dest.add(source)
        self.names.update(scene.names)
