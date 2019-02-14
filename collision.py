"""
Collision handling
"""

import logging

COLLISIONSIDE_NONE = 0
COLLISIONSIDE_TOP = 1
COLLISIONSIDE_BOTTOM = 2
COLLISIONSIDE_LEFT = 4
COLLISIONSIDE_RIGHT = 8

COLLISIONSIDE_TEXT = {
    COLLISIONSIDE_NONE: "None",
    COLLISIONSIDE_TOP: "Top",
    COLLISIONSIDE_BOTTOM: "Bottom",
    COLLISIONSIDE_LEFT: "Left",
    COLLISIONSIDE_RIGHT: "Right",
}


def find_closest(projectile, sprites):
    """Find sprite that is closest to projectile"""

    def keyfunc(sprite):
        """Sort by previous distance from center of previous position"""
        return rect_distance(projectile.last.center, sprite.last)

    closest = min(sprites, key=keyfunc)
    return closest


def rect_distance(point, rect):
    """Calculate the distance between a point and a rect"""
    delta_x = 0
    if point[0] < rect.left:
        delta_x = rect.left - point[0]
    elif rect.right - 1 < point[0]:
        delta_x = point[0] - (rect.right - 1)

    delta_y = 0
    if point[1] < rect.top:
        delta_y = rect.top - point[1]
    elif rect.bottom - 1 < point[1]:
        delta_y = point[1] - (rect.bottom - 1)

    return delta_x**2 + delta_y**2


def collision_move_to_edge(sprite1, sprite2):
    """Resolve collision by moving sprite1

    sprite1 is projectile, sprite2 is the other.
    Move sprite1 to be out of contact based on velocity
    """

    # Velocity1 alone keeps the ball path cleaner, but can be wonky when the paddle is moving fast
    # Relative velocity improves the overall response, but jerks the ball around with fast motion
    v1_x = sprite1.rect.centerx - sprite1.last.centerx
    v1_y = sprite1.rect.centery - sprite1.last.centery

    v2_x = sprite2.rect.centerx - sprite2.last.centerx
    v2_y = sprite2.rect.centery - sprite2.last.centery

    vel_x = v1_x - v2_x
    vel_y = v1_y - v2_y

    # Find the overlapping distances
    if vel_x >= 0:
        overlap_x = sprite1.rect.right - sprite2.rect.left
    else:
        overlap_x = sprite1.rect.left - sprite2.rect.right

    if vel_y >= 0:
        overlap_y = sprite1.rect.bottom - sprite2.rect.top
    else:
        overlap_y = sprite1.rect.top - sprite2.rect.bottom

    # Hack to account for 0 - just assume they're very small
    if vel_x == 0:
        vel_x = 0.00001

    if vel_y == 0:
        vel_y = 0.00001

    # Calculate the time to each edge, and rewind position by the minimum of the two
    time_x = overlap_x / float(vel_x)
    time_y = overlap_y / float(vel_y)
    if time_x < time_y:
        delta_x = -vel_x * time_x
        delta_y = -vel_y * time_x
    else:
        delta_x = -vel_x * time_y
        delta_y = -vel_y * time_y

    logging.info("Move: (%d, %d)", delta_x, delta_y)

    sprite1.rect.move_ip(int(delta_x), int(delta_y))


def collision_side(sprite1, sprite2):
    """Determine the side of collisions between 2 sprites"""
    result = collision_side_worker(sprite1, sprite2)
    logging.info("collision curr %s %s", sprite1.rect, sprite2.rect)
    logging.info("collision prev %s %s", sprite1.last, sprite2.last)
    logging.info("collision side %s", COLLISIONSIDE_TEXT[result])
    return result


def collision_side_worker(sprite1, sprite2):
    """Determine the side of collisions between 2 sprites

    Code from https://hopefultoad.blogspot.com/2017/09/code-example-for-2d-aabb-collision.html
    """

    corner_rise = 0
    corner_run = 0

    vel_rise_1 = sprite1.rect.centery - sprite1.last.centery
    vel_run_1 = sprite1.rect.centerx - sprite1.last.centerx

    vel_rise_2 = sprite2.rect.centery - sprite2.last.centery
    vel_run_2 = sprite2.rect.centerx - sprite2.last.centerx

    vel_rise = vel_rise_1 - vel_rise_2
    vel_run = vel_run_1 - vel_run_2
    sprite1_prev = sprite1.last.move(vel_run_2, vel_rise_2)

    # Stores what sides might have been collided with
    potential = COLLISIONSIDE_NONE

    if sprite1_prev.right <= sprite2.rect.left:
        # Did not collide with right side might have collided with left side
        potential |= COLLISIONSIDE_LEFT

        corner_run = sprite2.rect.left - sprite1_prev.right

        if sprite1_prev.bottom <= sprite2.rect.top:
            # Might have collided with top side
            potential |= COLLISIONSIDE_TOP
            corner_rise = sprite2.rect.top - sprite1_prev.bottom
        elif sprite1_prev.top >= sprite2.rect.bottom:
            # Might have collided with bottom side
            potential |= COLLISIONSIDE_BOTTOM
            corner_rise = sprite2.rect.bottom - sprite1_prev.top
        else:
            # Did not collide with top side or bottom side or right side
            return COLLISIONSIDE_LEFT
    elif sprite1_prev.left >= sprite2.rect.right:
        # Did not collide with left side might have collided with right side
        potential |= COLLISIONSIDE_RIGHT

        corner_run = sprite1_prev.left - sprite2.rect.right

        if sprite1_prev.bottom <= sprite2.rect.top:
            # Might have collided with top side
            potential |= COLLISIONSIDE_TOP
            corner_rise = sprite1_prev.bottom - sprite2.rect.top
        elif sprite1_prev.top >= sprite2.rect.bottom:
            # Might have collided with bottom side
            potential |= COLLISIONSIDE_BOTTOM
            corner_rise = sprite1_prev.top - sprite2.rect.bottom
        else:
            # Did not collide with top side or bottom side or left side
            return COLLISIONSIDE_RIGHT
    else:
        # Did not collide with either left or right side
        # must be top side, bottom side, or none
        if sprite1_prev.bottom <= sprite2.rect.top:
            return COLLISIONSIDE_TOP
        elif sprite1_prev.top >= sprite2.rect.bottom:
            return COLLISIONSIDE_BOTTOM
        else:
            # Previous hitbox of moving object was already colliding with stationary object
            return COLLISIONSIDE_NONE

    # Corner case might have collided with more than one side
    # Compare slopes to see which side was collided with
    return collide_slopes(potential,
                          vel_rise,
                          vel_run,
                          corner_rise,
                          corner_run)


def collide_slopes(potential, vel_rise, vel_run, corner_rise, corner_run):
    """Check for collision using slope between corners"""
    if vel_run == 0:
        vel_run = 0.001

    if corner_run == 0:
        corner_run = 0.001

    vel_slope = vel_rise / vel_run
    corner_slope = corner_rise / corner_run

    if (potential & COLLISIONSIDE_TOP) == COLLISIONSIDE_TOP:
        if (potential & COLLISIONSIDE_LEFT) == COLLISIONSIDE_LEFT:
            if vel_slope < corner_slope:
                return COLLISIONSIDE_TOP
            else:
                return COLLISIONSIDE_LEFT
        elif (potential & COLLISIONSIDE_RIGHT) == COLLISIONSIDE_RIGHT:
            if vel_slope > corner_slope:
                return COLLISIONSIDE_TOP
            else:
                return COLLISIONSIDE_RIGHT
    elif (potential & COLLISIONSIDE_BOTTOM) == COLLISIONSIDE_BOTTOM:
        if (potential & COLLISIONSIDE_LEFT) == COLLISIONSIDE_LEFT:
            if vel_slope > corner_slope:
                return COLLISIONSIDE_BOTTOM
            else:
                return COLLISIONSIDE_LEFT
        elif (potential & COLLISIONSIDE_RIGHT) == COLLISIONSIDE_RIGHT:
            if vel_slope < corner_slope:
                return COLLISIONSIDE_BOTTOM
            else:
                return COLLISIONSIDE_RIGHT
    return COLLISIONSIDE_NONE
