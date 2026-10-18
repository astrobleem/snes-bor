"""Complete field coverage and sealed raw-input provenance for fused captures.

Collection never creates or refreshes a seal. The retained seal is review-pinned;
fresh native suites seal their inputs once, immediately after capture. Subsequent
collection of another suite requires its explicitly supplied trusted digests.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


ROOT = Path(__file__).resolve().parents[2]
CASES = ('success', 'valid', 'early', 'ready', 'partial', 'stale',
         'insufficient', 'right')
PROVENANCE = 'capture-provenance.json'
RAW_MANIFEST = 'raw-inputs-before-certification.json'
# Shared immutable media is a hardlink and excluded from the original manifest.
# Bind it independently to the byte-identical accepted exact-coverage asset.
MSU_SHA256 = 'eb781b14d4df082f574df8eb58cb90d5714969a5a91913fdcbd70902da77b1cf'


@dataclass(frozen=True)
class CaptureSeal:
    provenance_sha256: str
    raw_manifest_sha256: str
    msu_sha256: str = MSU_SHA256


RETAINED_SEAL = CaptureSeal(
    '604e91dd9e2400b717134507fe36852b227fada66bb4c72b7571452f9c8edb5d',
    'edef6a159feea7efa141e66b7869c654aa78053d0a16262fc58200fc3ca7beef')


def require(ok, code):
    if not ok:
        raise ValueError('FUSED_CAPTURE:' + code)


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _json(raw, code):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError('FUSED_CAPTURE:' + code) from error


def _pinned_json(path, digest, code):
    require(_digest(digest), code + '_PIN')
    require(path.is_file() and not path.is_symlink(), code + '_FILE')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == digest, code + '_DIGEST')
    return _json(raw, code + '_JSON')


def _inside(path, parent, code):
    try:
        return path.relative_to(parent)
    except ValueError as error:
        raise ValueError('FUSED_CAPTURE:' + code) from error


def _path(value, base):
    require(isinstance(value, str) and bool(value), 'PATH_TYPE')
    parsed = PurePosixPath(value.replace('\\', '/'))
    require(not parsed.is_absolute() and '..' not in parsed.parts and
            ':' not in value and '\0' not in value, 'PATH_ESCAPE')
    path = base.joinpath(*parsed.parts).resolve()
    _inside(path, base, 'PATH_ESCAPE')
    return path


def verify_field_inventory(folder):
    """Require ordered indices, consecutive physical fields and exact captures."""
    native = folder / 'native'
    path = folder / 'fields.json'
    require(path.is_file() and not path.is_symlink(), folder.name + ':FIELDS_FILE')
    fields = _json(path.read_bytes(), folder.name + ':FIELDS_JSON')
    require(isinstance(fields, list) and bool(fields), folder.name + ':FIELDS_NONEMPTY')
    frames = []
    for index, field in enumerate(fields):
        require(isinstance(field, dict) and type(field.get('index')) is int and
                field['index'] == index, folder.name + ':FIELD_INDEX')
        ppu = field.get('ppu')
        require(isinstance(ppu, dict) and type(ppu.get('frameCount')) is int and
                ppu['frameCount'] >= 0, folder.name + ':FIELD_FRAME_TYPE')
        frames.append(ppu['frameCount'])
    require(frames == list(range(frames[0], frames[0] + len(fields))),
            folder.name + ':FIELD_FRAME_SEQUENCE')
    require(native.is_dir() and not native.is_symlink(), folder.name + ':NATIVE_DIRECTORY')
    for extension, key in (('png', 'screenshot_sha256'), ('vram', 'vram_sha256')):
        expected = {f'field-{i:04d}.{extension}' for i in range(len(fields))}
        actual = {p.relative_to(native).as_posix() for p in native.rglob('*')
                  if p.name.casefold().startswith('field-') and
                  p.suffix.casefold() == '.' + extension}
        require(actual == expected, folder.name + ':FIELD_' + extension.upper() + '_INVENTORY')
        for field in fields:
            capture = native / f"field-{field['index']:04d}.{extension}"
            require(capture.is_file() and not capture.is_symlink(),
                    folder.name + ':FIELD_' + extension.upper() + '_FILE')
            require(_digest(field.get(key)) and sha(capture) == field[key],
                    folder.name + ':FIELD_' + extension.upper() + '_HASH')
    return dict(fields=len(fields), first_frame=frames[0], last_frame=frames[-1],
                consecutive=True, exact_png_vram_inventory=True)


def _raw_paths(root):
    paths = set()
    for case in CASES:
        folder = root / case
        require(folder.is_dir() and not folder.is_symlink(), case + ':CASE_DIRECTORY')
        for name in ('contract.json', 'fields.json'):
            path = folder / name
            require(path.is_file() and not path.is_symlink(), case + ':RAW_FILE:' + name)
            paths.add(path.resolve())
        native = folder / 'native'
        require(native.is_dir() and not native.is_symlink(), case + ':NATIVE_DIRECTORY')
        for path in native.rglob('*'):
            require(not path.is_symlink(), case + ':RAW_SYMLINK')
            if path.is_dir():
                continue
            require(path.is_file(), case + ':RAW_FILE_TYPE')
            if path != native / 'bor.msu':
                paths.add(path.resolve())
    return paths


def _verify_msu(folder, digest):
    path = folder / 'native' / 'bor.msu'
    require(_digest(digest) and path.is_file() and not path.is_symlink() and
            sha(path) == digest, folder.name + ':MSU_INPUT_HASH')


def verify_capture(root, seal=RETAINED_SEAL, *, base=ROOT):
    """Validate sealed manifests and every raw origin/destination before use."""
    root, base = Path(root).resolve(), Path(base).resolve()
    _inside(root, base, 'ROOT_ESCAPE')
    provenance = _pinned_json(root / PROVENANCE, seal.provenance_sha256, 'PROVENANCE')
    raw = _pinned_json(root / RAW_MANIFEST, seal.raw_manifest_sha256, 'RAW_MANIFEST')
    require(isinstance(provenance, dict) and isinstance(provenance.get('case_roots'), dict)
            and set(provenance['case_roots']) == set(CASES), 'CASE_ROOTS')
    origins = {case: _path(value, base) for case, value in provenance['case_roots'].items()}
    require(len(set(origins.values())) == len(CASES) and
            all(path.name == case and path.is_dir() for case, path in origins.items()),
            'CASE_ORIGIN_IDENTITY')
    copies = provenance.get('copies')
    require(isinstance(copies, list) and bool(copies), 'COPIES_LIST')
    destinations, sources = {}, set()
    for entry in copies:
        require(isinstance(entry, dict) and set(entry) == {'source', 'destination', 'sha256'}
                and _digest(entry['sha256']), 'COPY_ENTRY')
        destination = _path(entry['destination'], base)
        relative = _inside(destination, root, 'COPY_DESTINATION_ESCAPE')
        require(len(relative.parts) >= 2 and relative.parts[0] in CASES, 'COPY_CASE')
        case = relative.parts[0]
        source = _path(entry['source'], base)
        require(source == origins[case].joinpath(*relative.parts[1:]).resolve(),
                'COPY_SOURCE_MAPPING')
        require(destination not in destinations and source not in sources, 'COPY_DUPLICATE')
        require(source.is_file() and sha(source) == entry['sha256'], 'COPY_SOURCE_HASH')
        sources.add(source)
        destinations[destination] = (source, entry['sha256'])
    require(isinstance(raw, list) and bool(raw), 'RAW_LIST')
    declared = {}
    for entry in raw:
        require(isinstance(entry, dict) and set(entry) == {'path', 'sha256'} and
                _digest(entry['sha256']), 'RAW_ENTRY')
        path = _path(entry['path'], base)
        _inside(path, root, 'RAW_PATH_ESCAPE')
        require(path not in declared, 'RAW_DUPLICATE')
        declared[path] = entry['sha256']
    require(set(declared) == _raw_paths(root), 'RAW_INVENTORY')
    for path, digest in declared.items():
        require(path in destinations and destinations[path][1] == digest, 'RAW_PROVENANCE_MAPPING')
        require(sha(path) == digest, 'RAW_INPUT_HASH:' + path.name)
    for case in CASES:
        _verify_msu(root / case, seal.msu_sha256)
        _verify_msu(origins[case], seal.msu_sha256)
    coverage = {case: verify_field_inventory(root / case) for case in CASES}
    return dict(provenance_sha256=seal.provenance_sha256,
                raw_manifest_sha256=seal.raw_manifest_sha256,
                immutable_msu_sha256=seal.msu_sha256,
                raw_inputs=len(declared), verified_origins=len(destinations),
                cases=coverage, observed_fields=sum(x['fields'] for x in coverage.values()))


def seal_native_capture(root, *, base=ROOT, msu_sha256=MSU_SHA256):
    """Seal a just-completed native suite once; never called by collect_suite."""
    root, base = Path(root).resolve(), Path(base).resolve()
    _inside(root, base, 'ROOT_ESCAPE')
    require(not (root / PROVENANCE).exists() and not (root / RAW_MANIFEST).exists(),
            'SEAL_ALREADY_EXISTS')
    for case in CASES:
        verify_field_inventory(root / case)
        _verify_msu(root / case, msu_sha256)
    rows = [dict(path=path.relative_to(base).as_posix(), sha256=sha(path))
            for path in sorted(_raw_paths(root))]
    copies = [dict(source=row['path'], destination=row['path'], sha256=row['sha256'])
              for row in rows]
    provenance = dict(case_roots={case: (root / case).relative_to(base).as_posix()
                                  for case in CASES}, copies=copies,
                      origin='fresh native suite; sealed before collection')
    for name, value in ((PROVENANCE, provenance), (RAW_MANIFEST, rows)):
        with (root / name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')
    return CaptureSeal(sha(root / PROVENANCE), sha(root / RAW_MANIFEST), msu_sha256)
