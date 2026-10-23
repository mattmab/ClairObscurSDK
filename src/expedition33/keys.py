"""Canonical single-key names for the Windows input adapter.

These are virtual-key codes, not assumed Unreal FKey layouts. Modifier chords,
mouse buttons and controller inputs are outside the initial adapter contract.
"""
VIRTUAL_KEYS = {
    **{chr(code): code for code in range(65, 91)},
    **{str(number): 48 + number for number in range(10)},
    **{f'F{number}': 111 + number for number in range(1, 13)},
    'Backspace': 8, 'Tab': 9, 'Enter': 13, 'Escape': 27, 'Space': 32,
    'PageUp': 33, 'PageDown': 34, 'End': 35, 'Home': 36,
    ',': 188, '.': 190,
    'Left': 37, 'Up': 38, 'Right': 39, 'Down': 40, 'Insert': 45, 'Delete': 46,
}
KEY_NAMES = tuple(VIRTUAL_KEYS)
_NAMES = {name.casefold(): name for name in KEY_NAMES}
_NAMES.update({'comma': ',', 'period': '.', 'dot': '.'})


def normalize_key(value):
    if value is None:
        return None
    if type(value) is not str or value.casefold() not in _NAMES:
        raise ValueError('Expected a supported single key name or None to unbind')
    return _NAMES[value.casefold()]
