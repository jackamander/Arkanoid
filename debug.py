"""
debug assistance
"""
import logging

import pygame

import display
import engine
import main
import utils

class CollisionTest(engine.State):
    def __init__(self, eng):
        engine.State.__init__(self, eng)

        self.scenes = {scene : display.Scene(scene, eng.vars) for scene in ["debug"]}
        self.engine = eng

        self.ball = self.scenes["debug"].names["ball"]
        self.brick = self.scenes["debug"].names["brick"]

        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)

    def on_keydown(self, event):
        delta = [0,0]

        if event.key == pygame.K_UP:
            delta = [0,-1]
        elif event.key == pygame.K_DOWN:
            delta = [0,1]
        elif event.key == pygame.K_LEFT:
            delta = [-1,0]
        elif event.key == pygame.K_RIGHT:
            delta = [1,0]

        self.scenes["debug"].names["ball"].move(delta)

        if pygame.sprite.collide_rect(self.ball, self.brick):
            side = engine.collision_side(self.ball, self.brick)
            print side
        else:
            print

    def update(self):
        for scene in self.scenes.values():
            scene.group.update()

    def draw(self, screen):
        for scene in self.scenes.values():
            scene.group.draw(screen)


if __name__ == "__main__":
    utils.setup_logging("logging.json")

    engine.Engine.INITIAL_STATE = CollisionTest

    try:
        main.main()
    except Exception as exc:
        logging.exception("Uncaught exception!")
