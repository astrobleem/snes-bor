"""Small source-of-truth parser for BOR LEVELS.TXT set declarations."""

from dataclasses import dataclass, field

from pak_extract import extract


@dataclass
class BorSet:
    set_id: int
    name: str
    ifcomplete: int = 0
    entries: list = field(default_factory=list)


def parse_levels(text):
    sets = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        directive = parts[0].lower()
        if directive == 'set':
            if len(parts) != 2:
                raise ValueError('malformed BOR set declaration')
            current = BorSet(len(sets), parts[1])
            sets.append(current)
        elif current is None:
            raise ValueError(f'BOR directive before set: {line}')
        elif directive == 'ifcomplete':
            if len(parts) != 2:
                raise ValueError('malformed BOR ifcomplete declaration')
            current.ifcomplete = int(parts[1], 10)
            current.entries.append((directive, parts[1]))
        elif directive in ('file', 'scene', 'next'):
            current.entries.append((directive, ' '.join(parts[1:])))
        else:
            raise ValueError(f'unknown BOR LEVELS directive: {line}')
    if not sets:
        raise ValueError('BOR LEVELS.TXT contains no sets')
    return sets


def parse_levels_from_pak(pak_path, entry='DATA\\LEVELS.TXT'):
    return parse_levels(extract(pak_path, entry).decode('latin1'))
