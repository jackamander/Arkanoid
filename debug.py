"""
debug assistance
"""
import logging

import pygame

import display
import engine
import main
import utils

SCENES = {
    "collision_test": [
        {
            "name": "ball",
            "image": "ball",
            "position": [100, 80]
        },
        {
            "name": "brick",
            "image": "red",
            "position": [100, 100]
        }
    ]
}


class DebugState(engine.State):
    def __init__(self, eng, data):
        engine.State.__init__(self, eng, data)

        # Register the faux JSON from the debug file
        utils.config["scenes"].update(SCENES)


class CollisionTest(DebugState):
    def __init__(self, eng, data):
        DebugState.__init__(self, eng, data)

        self.scene = display.Scene(["collision_test"], eng.vars)

        self.ball = self.scene.names["ball"]
        self.brick = self.scene.names["brick"]

        utils.events.register(utils.EVT_KEYDOWN, self.on_keydown)

    def on_keydown(self, event):
        delta = [0, 0]

        if event.key == pygame.K_UP:
            delta = [0, -1]
        elif event.key == pygame.K_DOWN:
            delta = [0, 1]
        elif event.key == pygame.K_LEFT:
            delta = [-1, 0]
        elif event.key == pygame.K_RIGHT:
            delta = [1, 0]

        self.scene.names["ball"].rect.move_ip(delta)

        if pygame.sprite.collide_rect(self.ball, self.brick):
            side = engine.collision_side(self.ball, self.brick)
            print(side)
        else:
            print()

    def update(self):
        self.scene.groups["all"].update()

    def draw(self, screen):
        self.scene.groups["all"].draw(screen)


class DebugEngine(engine.Engine):
    def __init__(self):
        engine.Engine.__init__(self)
        self.__running = True

    def pause_on(self):
        self.__running = False
        display.release_mouse()

    def pause_off(self):
        self.__running = True
        display.grab_mouse()

    def pause_toggle(self):
        if self.__running:
            self.pause_on()
        else:
            self.pause_off()

    def input(self, event):
        if event.type == utils.EVT_KEYDOWN:
            if event.key == pygame.K_n:
                self.state.next_level()
            elif event.key == pygame.K_l:
                self.state.jump_level(36)
            elif event.key == pygame.K_r:
                self.set_state(engine.StartState)
            elif event.key == pygame.K_p:
                self.pause_toggle()
            elif event.key == pygame.K_s:
                if self.__running:
                    self.pause_on()
                else:
                    self.step()

        if self.__running:
            engine.Engine.input(self, event)

    def update(self):
        if self.__running:
            self.step()

    def step(self):
        engine.Engine.update(self)


if __name__ == "__main__":
    utils.setup_logging("logging.json")

    main.ENGINE_CLASS = DebugEngine

    # engine.Engine.INITIAL_STATE = CollisionTest

    try:
        main.main()
    except Exception as exc:
        logging.exception("Uncaught exception!")
