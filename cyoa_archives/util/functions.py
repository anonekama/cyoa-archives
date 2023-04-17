def calc_intersect(xmin_a, xmax_a, ymin_a, ymax_a, xmin_b, xmax_b, ymin_b, ymax_b):
    dx = min(xmax_a, xmax_b) - max(xmin_a, xmin_b)
    dy = min(ymax_a, ymax_b) - max(ymin_a, ymin_b)
    if (dx > 0) and (dy > 0):
        return dx * dy
    return 0
