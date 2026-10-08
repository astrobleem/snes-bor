"""Compiler guards for returning jobs at a persistent SA-1 poll safepoint."""


def lorom_offset(address):
    if address & 0xffff < 0x8000:
        raise ValueError('WORKSPACE_POLL_NOT_ROM')
    return (address >> 16) * 32768 + (address & 65535) - 32768


def install_workspace_gate(rom, worker_symbols, main_symbols):
    """Opt in at the existing post-world mutation-fence boundary only."""
    at = lorom_offset(worker_symbols['Worker_NoFault'])
    original = bytes.fromhex('af 0c 20 41')
    if rom[at:at + 4] != original:
        raise ValueError('WORKSPACE_POLL_SOURCE_LAYOUT')
    target = main_symbols['SourceWorkspaceSA1_Poll']
    if target >> 16 == 0:
        raise ValueError('WORKSPACE_POLL_BANK_ZERO_FORBIDDEN')
    rom[at:at + 4] = b'\x22' + target.to_bytes(3, 'little')
    return dict(address=worker_symbols['Worker_NoFault'], original=original.hex(),
                target=target, bytes=4, opt_in=True)


def returning_audio_kernel(kernel, *, encoder=False):
    """Retain instruction addresses, caller native mode, and the worker stack.

    Isolated kernels reset SP and use a private BW-RAM completion marker.
    Live jobs must preserve SP and relocate markers out of the source tick
    ring. Encoder scratch must also avoid the legacy worker mailbox.
    """
    prefix = bytes.fromhex('78 18 fb c2 30 a2 ff 37 9a')
    if kernel[:len(prefix)] != prefix:
        raise ValueError('WORKSPACE_AUDIO_BOOTSTRAP_LAYOUT')
    kernel = bytes.fromhex('78 ea ea c2 30 ea ea ea ea') + kernel[len(prefix):]
    for before, after in [('8f f0 3f 41', '8f d0 34 00'),
                          ('8f f2 3f 41', '8f d2 34 00')]:
        kernel = kernel.replace(bytes.fromhex(before), bytes.fromhex(after))
    if encoder:
        before = bytes.fromhex('a9 00 30 5b')
        if kernel.count(before) != 1:
            raise ValueError('WORKSPACE_ENCODER_SCRATCH_LAYOUT')
        kernel = kernel.replace(before, bytes.fromhex('a9 a0 34 5b'))
    return kernel
