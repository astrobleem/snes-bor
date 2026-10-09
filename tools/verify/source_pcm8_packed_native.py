"""Isolated packed PCM8 gather with 24-bit ROM pointers and source Q12 state.

Integer-stride, equal-gain projection only. This owns private fixture memory;
it does not publish a production audio lease or admit source callbacks.
"""
import struct
from m4_sound_gather_mix_sa1_native import build as bounded
from m4_sound_mix_sa1_native import Code


def build(frames, volume, inputs, *, batches=1, source_bank=0xe0,
          source_offset=0, packed_mono=False, active_mode=1):
    count = len(inputs)
    if not 1 <= count <= 12 or not 1 <= frames <= 184 or not 1 <= batches <= 1024:
        raise ValueError('PACKED_PCM8_JOB_DOMAIN')
    if not 0 <= volume <= 64 or active_mode not in (1, 2):
        raise ValueError('PACKED_PCM8_GAIN_ACTIVE_DOMAIN')
    if not 0xc2 <= source_bank <= 0xff or not 0 <= source_offset < 65536 or source_offset & 1:
        raise ValueError('PACKED_PCM8_ROM_BASE')
    for row in inputs:
        if not 0 < len(row['values']) <= 524287 or not 0 <= row['initial_Q12'] < len(row['values'])*4096 or any(not 0 <= v <= 255 for v in row['values']):
            raise ValueError('PACKED_PCM8_SOURCE_DOMAIN')
    start = (source_bank-0xc0)*65536+source_offset
    end = start+sum(len(r['values'])*2 for r in inputs)
    if end > 0x400000:
        raise ValueError('PACKED_PCM8_ROM_CAPACITY')
    dummy = [dict(values=[128]*257, initial_Q12=0) for _ in inputs]
    raw, _, old = bounded(frames, 4096, volume, False, expanded_byte_sum=True,
                         completion=True, input_channels=dummy, packed_mono=packed_mono)
    rom = bytearray(raw)
    size = max(len(rom), 1 << (end-1).bit_length())
    rom.extend(bytes([255])*(size-len(rom)))
    rom[0x7fd7] = size.bit_length()-11
    bases = []
    cursor = start
    for row in inputs:
        bases.append(0xc00000+cursor)
        data = struct.pack('<'+'H'*len(row['values']), *row['values'])
        rom[cursor:cursor+len(data)] = data
        cursor += len(data)
    for at, values in ((0x1a400, [r['initial_Q12'] for r in inputs]),
                       (0x1a430, [active_mode]*count),
                       (0x1a460, [len(r['values'])*2 for r in inputs]),
                       (0x1a490, bases)):
        rom[at:at+48] = b''.join(struct.pack('<I', v) for v in values)+bytes(48-count*4)
    c = Code(0x3500)
    c.emit('78 18 fb c2 30 a2 ff 37 9a a9 e0 34 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 00 48 ab c2 20')
    c.word(0xa9, batches); c.emit('85 14')
    c.label('entry'); c.emit('a9 00 00 a2 00 00')
    c.label('clear'); c.emit('9d 00 32 e8 e8'); c.word(0xe0, frames*4)
    c.branch(0xd0, 'clear'); c.emit('85 06 e2 20 8d 50 22 c2 20')
    c.label('channel'); c.emit('a6 06 bf 00 51 43 85 12')
    c.branch(0xd0, 'live'); c.jump('next_channel'); c.label('live')
    # Logical byte offset is a 32-bit value at DP02/16. DP00 retains the
    # source fractional Q12 bits. DP20..22 is an actual 24-bit ROM pointer.
    c.emit('bf 00 50 43 29 ff 0f 85 00 bf 00 50 43 eb 29 ff 00 4a 4a 4a 4a 85 02 bf 02 50 43 0a 0a 0a 0a 05 02 0a 85 02 bf 02 50 43')
    c.emit('4a '*11); c.emit('85 16 bf 60 a4 03 85 10 bf 62 a4 03 85 18 bf 90 a4 03 85 04 bf 92 a4 03 85 1a')
    c.emit('a5 04 18 65 02 85 20 a5 1a 65 16 85 22 a0 00 00')
    c.word(0xa9, frames); c.emit('85 08')
    c.label('sample'); c.emit('a7 20 18 79 00 32 99 00 32')
    c.word(0xb9, 0x3200+frames*2); c.emit('1a'); c.word(0x99, 0x3200+frames*2)
    c.emit('c8 c8 a5 20 18 69 02 00 85 20')
    c.branch(0x90, 'pointer_inside'); c.emit('e6 22'); c.label('pointer_inside')
    c.emit('a5 02 18 69 02 00 85 02'); c.branch(0x90, 'index_inside')
    c.emit('e6 16'); c.label('index_inside')
    c.emit('a5 16 c5 18'); c.branch(0x90, 'inside')
    c.branch(0xd0, 'end'); c.emit('a5 02 c5 10'); c.branch(0x90, 'inside')
    c.label('end'); c.emit('a5 02 38 e5 10 85 02 a5 16 e5 18 85 16 a5 12 c9 02 00')
    c.branch(0xf0, 'loop'); c.emit('a9 00 00 85 12'); c.jump('samples_done')
    c.label('loop'); c.emit('a5 04 18 65 02 85 20 a5 1a 65 16 85 22')
    c.label('inside'); c.emit('c6 08'); c.branch(0xf0, 'samples_done'); c.jump('sample')
    c.label('samples_done'); c.emit('a5 02 29 1f 00'); c.emit('0a '*11)
    c.emit('05 00 a6 06 9f 00 50 43 a5 02'); c.emit('4a '*5)
    c.emit('85 0a a5 16'); c.emit('0a '*11)
    c.emit('05 0a 9f 02 50 43 a5 12 9f 00 51 43 a9 00 00 9f 02 51 43')
    c.label('next_channel'); c.emit('a5 06 18 69 04 00 85 06'); c.word(0xc9, count*4)
    c.branch(0xf0, 'gather_mix_done'); c.jump('channel')
    c.label('gather_mix_done'); c.emit('a0 00 00')
    # Exactly the bounded worker's signed multiply, active-count bias,
    # saturation and equal-gain output. The arithmetic is shared bytecode.
    clip = old[old.index(bytes.fromhex('b9 00 32 8d 51 22')):]
    stop = clip.index(bytes.fromhex('a9 ab b4 8f f0 3f 41'))
    clip = bytearray(clip[:stop])
    # Its final BNE points to the first byte of the copied clip region.
    c.data.extend(clip)
    c.label('done'); c.emit('c6 14'); c.branch(0xf0, 'final_done'); c.jump('entry')
    c.label('final_done'); c.emit('a9 ab b4 8f f0 3f 41')
    c.label('stop'); c.jump('stop')
    worker = c.finish()
    if len(worker) > 0x2c0:
        raise ValueError('PACKED_PCM8_IRAM_STACK_GAP')
    rom[0x9000:0x9000+len(worker)] = worker
    host = bytearray(rom[0x8000:0x8400])
    needle = bytes.fromhex('bf 00 90 01 9f 00 35 00 e8 e0')
    at = host.index(needle)+len(needle)
    host[at:at+2] = struct.pack('<H', len(worker))
    rom[0x8000:0x8400] = host
    return bytes(rom), {n:0x3500+c.labels[n] for n in ('entry','gather_mix_done','done')}, worker
