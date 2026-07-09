from repcounter.count import RepCounter


def feed(counter: RepCounter, angles, visibility: float = 1.0):
    return [counter.update(angle, visibility) for angle in angles]
