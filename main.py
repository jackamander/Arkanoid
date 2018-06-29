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


def main():
    """Main loop"""

    config = utils.get_config("config.json")

    pygame.init()

    camera = display.Camera(config)

    # Mainloop
    clock = pygame.time.Clock()

    eng = engine.Engine(config)

    while True:

        # Event pump
        for event in pygame.event.get():
            logging.debug("Event: %s", pygame.event.event_name(event.type))

            if event.type == pygame.QUIT:
                return

            eng.input(event)

        eng.draw(camera)

        fps = str(int(clock.get_fps()))
        camera.draw_text(fps, (0, 0))

        clock.tick(config["frame_rate"])
        pygame.display.flip()

if __name__ == '__main__':
    utils.setup_logging("logging.json")

    try:
        main()
    except Exception as exc:
        logging.exception("Uncaught exception!")
