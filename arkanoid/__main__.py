"""Arkanoid clone"""

import inspect
import logging
import os
import sys

import utils

def get_script_dir():
    """Get directory that includes this script.  Pulled from
    https://stackoverflow.com/questions/3718657/how-to-properly-determine-current-script-directory/22881871#22881871
    """
    if getattr(sys, 'frozen', False):  # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    path = os.path.realpath(path)
    return os.path.dirname(path)


def main():
    """Top level function"""

    # No PYC files
    sys.dont_write_bytecode = True

    # Switch to the install directory to load data files
    pathname = get_script_dir()
    os.chdir(pathname)
    sys.path.append(pathname)

    # Enable logging
    utils.setup_logging("logging.json")

    sys.stdout = utils.StreamToFunc(logging.info, "<stdout>")
    sys.stderr = utils.StreamToFunc(logging.error, "<stderr>")

    # Run the game
    try:
        import engine
        engine.main_loop()
    except:    # pylint: disable=bare-except
        logging.exception("Uncaught exception!")


if __name__ == '__main__':
    main()
