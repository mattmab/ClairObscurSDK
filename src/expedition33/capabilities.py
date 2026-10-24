"""Native protocol diagnostics; advertisements are not permission or readiness."""
from dataclasses import dataclass
import re

_NAME = re.compile(r'[a-z][a-z0-9_]*_protocol\Z')


@dataclass(frozen=True)
class ProtocolAdvertisement:
    name: str
    version: int | None
    state: str


@dataclass(frozen=True)
class CapabilitySnapshot:
    """Copied diagnostics, safe to retain after scope retirement.

    Explicit version matching never assumes newer versions are compatible.
    This does not replace supports_* prerequisites or native operation preflight.
    """
    protocols: tuple[ProtocolAdvertisement, ...]

    def protocol(self, name: str) -> ProtocolAdvertisement:
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise ValueError('Expected a native *_protocol name')
        return next((entry for entry in self.protocols if entry.name == name),
                    ProtocolAdvertisement(name, None, 'missing'))

    def matches(self, name: str, version: int) -> bool:
        if type(version) is not int or not 0 < version < 2**32:
            raise ValueError('Expected a positive uint32 protocol version')
        entry = self.protocol(name)
        return entry.state == 'advertised' and entry.version == version


def _snapshot(transport) -> CapabilitySnapshot:
    # Stored attributes only: no getters, commands, handles or session tokens.
    entries = []
    for name, value in sorted(vars(transport).items()):
        if not _NAME.fullmatch(name):
            continue
        valid = type(value) is int and 0 <= value < 2**32
        state = 'invalid' if not valid else 'disabled' if value == 0 else 'advertised'
        entries.append(ProtocolAdvertisement(name, value if valid else None, state))
    return CapabilitySnapshot(tuple(entries))
