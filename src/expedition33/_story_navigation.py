"""Decode the engine's navigation receipts for the owned Story option."""


def direction_events(observations):
    directions = {0: 'previous', 1: 'next'}
    return tuple((event.monotonic_ms, directions[code])
                 for event in observations
                 if (code := event.arguments['UINavigation']) in directions)
