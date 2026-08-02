#!/usr/bin/env python3
"""Reader for OpenBOR .pak archives.

Format (reverse-engineered from OpenBOR's own source,
source/gamelib/packfile.c -- there is no compression or real encryption,
despite "encrypted archive" being the common description in BOR community
docs):

    [4-byte magic "PACK"] [4-byte version, always 0] [file data ...]
    [directory entries ...] [4-byte offset back to the first directory entry]

Each directory entry is:

    [4-byte structsize] [4-byte filestart] [4-byte filesize] [name, NUL-terminated]

structsize = 12 + len(name) + 1 (all integers little-endian). The directory
is a flat list -- there is no real subdirectory nesting, just '\\'-separated
path components baked into each entry's name (e.g. "DATA\\CHARS\\RALF\\IDLE1.GIF").
"""
import struct
import sys

MAGIC = b'PACK'


class PakEntry:
    __slots__ = ('name', 'offset', 'size')

    def __init__(self, name, offset, size):
        self.name = name
        self.offset = offset
        self.size = size

    def __repr__(self):
        return f'PakEntry({self.name!r}, offset={self.offset}, size={self.size})'


def read_entries(pak_path):
    with open(pak_path, 'rb') as f:
        header = f.read(8)
        if header[:4] != MAGIC:
            raise ValueError(f'{pak_path}: not a PACK file (magic={header[:4]!r})')

        f.seek(0, 2)
        size = f.tell()
        f.seek(size - 4)
        dir_offset = struct.unpack('<I', f.read(4))[0]

        f.seek(dir_offset)
        entries = []
        while f.tell() < size - 4:
            structsize_bytes = f.read(4)
            if len(structsize_bytes) < 4:
                break
            structsize = struct.unpack('<I', structsize_bytes)[0]
            if structsize == 0:
                break
            filestart, filesize = struct.unpack('<II', f.read(8))
            name_len = structsize - 12
            name = f.read(name_len).split(b'\x00')[0].decode('latin1')
            entries.append(PakEntry(name, filestart, filesize))
        return entries


def extract(pak_path, entry_name):
    """Return the raw bytes of one entry, matched case-insensitively."""
    entries = read_entries(pak_path)
    matches = [e for e in entries if e.name.upper() == entry_name.upper()]
    if not matches:
        raise KeyError(f'{entry_name!r} not found in {pak_path}')
    entry = matches[0]
    with open(pak_path, 'rb') as f:
        f.seek(entry.offset)
        return f.read(entry.size)


def main():
    if len(sys.argv) < 2:
        print('usage: pak_extract.py <pak_path> [name_filter]', file=sys.stderr)
        raise SystemExit(1)
    pak_path = sys.argv[1]
    name_filter = sys.argv[2].upper() if len(sys.argv) > 2 else None
    entries = read_entries(pak_path)
    print(f'{len(entries)} entries')
    for e in entries:
        if name_filter is None or name_filter in e.name.upper():
            print(f'{e.offset}\t{e.size}\t{e.name}')


if __name__ == '__main__':
    main()
