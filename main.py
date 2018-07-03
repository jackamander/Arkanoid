"""
Arkanoid clone

Goal is to produce a complete game without having to worry about any game design or resources.  Just code!
"""

import logging
import os

import pygame

import display
import engine
import utils

def init():
    utils.config = utils.get_config("config.json")

def main():
    """Main loop"""
    pygame.init()

    camera = display.Camera()
    pygame.display.set_caption(utils.config["title"])

    # Mainloop
    clock = pygame.time.Clock()

    eng = engine.Engine()

    while True:

        # Event pump
        for event in pygame.event.get():
            logging.debug("Event: %s", pygame.event.event_name(event.type))

            if event.type == pygame.QUIT:
                return

            eng.input(event)

        eng.update()

        eng.draw(camera)

        fps = str(int(clock.get_fps()))
        camera.screen.blit(display.draw_text(fps), (0, 0))

        clock.tick(utils.config["frame_rate"])
        pygame.display.flip()

if __name__ == '__main__':
    utils.setup_logging("logging.json")

    try:
        init()
        main()
    except Exception as exc:
        logging.exception("Uncaught exception!")
