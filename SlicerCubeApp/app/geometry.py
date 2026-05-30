from math import sqrt

def pointInConvexPolygon(pt, poly):
    x, y = pt
    n = len(poly)
    if n < 3:
        return False

    def crossToPoint(start, end):
        start_x, start_y = start
        end_x, end_y = end
        return (end_x - start_x) * (y - start_y) - (end_y - start_y) * (x - start_x)

    sign = None
    for i in range(n):
        c = crossToPoint(poly[i], poly[(i + 1) % n])
        if c != 0:
            if sign is None:
                sign = 1 if c > 0 else -1
            elif (c > 0) != (sign > 0):
                return False
    return True


def distancePointToSegment(px, py, x1, y1, x2, y2):
    vx = x2 - x1
    vy = y2 - y1
    wx = px - x1
    wy = py - y1

    seg_len_sq = vx * vx + vy * vy
    if seg_len_sq == 0:
        return sqrt((px - x1) ** 2 + (py - y1) ** 2)

    t = (wx * vx + wy * vy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * vx
    proj_y = y1 + t * vy
    dx = px - proj_x
    dy = py - proj_y
    return sqrt(dx * dx + dy * dy)
