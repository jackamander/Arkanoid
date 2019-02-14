# Arkanoid Clone

## Goal
I've wanted to write games for a long time, but I've struggled to get much past the prototype phase.  My typical process looks like this:
1. Get excited about an idea
2. Hack out a prototype and play around with it
3. Go crazy trying to get the perfect clean architecture
4. Make changes to the game design that the architecture won't support
5. Repeat steps 3 and 4 ad nauseum until I get frustrated and give up.

To break this cycle, I decided to eliminate every question of game design and just focus on architecture.  To that end, I decided to clone Arkanoid, one of my favorite NES games from my childhood.  It's a simple, fun game that should work well with mouse and keyboard.

My goal is to clone Arkanoid and complete a full game.

## Technologies
Arknoid is an old game, so performance won't be an issue.  I want to focus on code architecture.  So, I've chosen the following technologies:
1. **Python 3**.  I love writing Python code - the speed of code construction and quality of the resulting code is outstanding.  The performance will be more than enough for this game.  Maybe later I will try to port this into C++ or C# to build my chops with a more traditional game language.  Until now, I've only used Python 2.7, but I'll use this as a springboard to learn Python 3.
2. **Pygame**.  I don't really like Pygame all that much - I really just use it as a thin SDL wrapper.  But, I know it well enough to make quick progress, and again, Arkanoid is pretty simple.
1. **VS Code**.  I freaking love VS Code.  I'll use the Python plug-in extensively.
3. **Github**.  I love git, and want to use this for my first Github project.  I'll try to follow best practices for setting up a good folder structure.
4. **Virtualenv**.  I'll use a virtual environment to try to control dependencies.  I plan to use the built-in **venv** from the Python standard library.
5. **unittest**.  I like the built-in unittest, and see no reason to use a 3rd party package.
6. **py2exe**.  I will freeze the scripts into a stand-alone Windows executable for "distribution."
7. **logging**.  No hacky print statements - let's use the logging capabilities in Python like an adult.
8. **cProfile, pdb, trace, tracemalloc, gc**.  The Python standard library is awesome!
9. **pydoc**.  I don't need docs for this, but I plan to experiment with PyDoc to document the design for my own reference.
10. **Pylint**.  I'll make sure the code has no Pylint errors (allowing for exceptions in the code comments).
11. **pep8**.  I'll try to follow pep8 for formatting.
12. **Others?**.  I plan to investigate a few others:  ```coverage.py``` for code coverage analysis, mypy for type annotations, automated test generation tools, statistical debugging tools, symbolic execution tools, etc.  I'm not sure what's out there for Python.

## Resources
Part of my goal here is to avoid having to worry about art, animations, music, sound effects, etc.  So, I will shamelessly steal resources from the web.  I do not own any of the resources, I will never try to commercialize this project, it is purely done for academic, educational purposes.

## Architecture
The basic game structure will be a state machine.  For the game mechanics, I plan to use an OOP approach first, using a Command pattern for sprite activities.  I want the application to be heavily data-driven, with configuration data in JSON (in keeping with the Python standard library theme).

Once I have a working game, I'd like to investigate an ECS pattern, as the types of games I'm drawn too generally benefit from that pattern as well.

## Implementation Notes

### Initial effort
I plowed through this over the summer of 2018.  My goal was to avoid overthinking the architecture, and just crunch out the game.  I used Youtube to remind myself of the game behavior, and found resources online for all the graphics and sounds from the original NES version of the game.  Happily, I was able to get the full game working!  There are a couple little bugs, but it's very playable (and actually pretty easy with my liberal capsule rules).  Architecturally, I'm not very happy.  I stayed true to my goal, but ended up with a pretty crusty first attempt.  There's a lot of game logic in code rather than data, and a lot of hacky features.

### Refactor Scoping
Before I finished the game, I lost discipline and started two parallel refactor efforts (because that's a great idea, right?).  I spent several hours working on a rough ECS effort, and then also pursued more tactical clean-up on a different branch.  Neither was that successful.  I'm treating those efforts as exploratory now, and once I finish the game with polish, I'll circle back and execute a real, systematic refactor.

### Testing
My initial test coverage stinks, which is my bad habit.  I tried to follow a contract-based approach with asserts, but that wasn't too thorough either.  I'll fix this while adding polish.

### Debugging
Likewise, my debug tools aren't great.  I didn't encounter very many tricky bugs, thankfully, but I'll need better tools to find the last bugs.  I have ideas for adding features during my polish stage.

### Requirements
It won't surprise you by now to know that I didn't document any requirements.  I will fix that during the refactor and test coverage exercises.

Some high-level requirements:
- Play with mouse only
- Play with keyboard only
- Level designer for bonus points

## Remaining Work
### Polish
- Convert to Python 3
- Pylint, pep8
- Virtual environment
- Command-line options
- Unit tests and code analysis
- Code coverage
- Profiling
- Better debug tools
- Windows executable
- Release to Github

### Refactor
- OOP clean-up
- ECS redesign