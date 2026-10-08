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


def entry_trampoline(target):
    """Select a compiled high-IRAM job without colliding with its row worker."""
    if not 0x003200 <= target < 0x0037c0:
        raise ValueError('WORKSPACE_JOB_ENTRY_RANGE')
    return b'\x5c' + target.to_bytes(3, 'little')


def returning_graphics_kernel(kernel, entries):
    """Adapt a sealed two-pose producer to one returning job per caller epoch.

    Keep instruction addresses for existing branches. The caller owns phase
    at $3416 and immutable context inputs; every completed bitmap is separate
    from publication. Scratch and diagnostics avoid the resident mailbox and
    source tick ring. This adapter does not bind a live camera/frame owner.
    """
    code = bytearray(returning_audio_kernel(kernel))
    dp = bytes.fromhex('a9 00 30 5b')
    phase = bytes.fromhex('a9 00 00 85 16 85 18')
    if code.count(dp) != 1 or code.count(phase) != 1:
        raise ValueError('WORKSPACE_GRAPHICS_BOOTSTRAP_LAYOUT')
    code = code.replace(dp, bytes.fromhex('a9 00 34 5b'))
    code = code.replace(phase, bytes.fromhex('ea ea ea ea ea 64 18'))
    for low in (0xf4, 0xf6, 0xf8):
        code = code.replace(bytes((0x8f, low, 0x3f, 0x41)),
                            bytes((0x8f, low - 0x20, 0x34, 0x00)))
    done = entries['done'] - 0x3200
    first_fault = min(entries[n] - 0x3200 for n in ('epoch_fault', 'fixed_actor_fault'))
    if code[done:done + 2] != bytes.fromhex('a5 12'):
        raise ValueError('WORKSPACE_GRAPHICS_COMPLETION_LAYOUT')
    finish = bytes.fromhex('a5 12 8f d6 34 00 a5 14 8f d8 34 00 e2 20 a9 00 8f 30 22 00 c2 20 a9 ab b4 8f d0 34 00 18 6b')
    if done + len(finish) > first_fault:
        raise ValueError('WORKSPACE_GRAPHICS_RETURN_CAPACITY')
    code[done:first_fault] = finish + b'\xea' * (first_fault - done - len(finish))
    for name in ('epoch_fault', 'fixed_actor_fault'):
        at = entries[name] - 0x3200
        if code[at] != 0xa9 or code[at + 3:at + 7] != bytes.fromhex('8f d0 34 00') or code[at + 7] != 0x4c:
            raise ValueError('WORKSPACE_GRAPHICS_FAULT_LAYOUT')
        code[at + 7:at + 10] = bytes.fromhex('38 6b ea')
    return bytes(code)


def returning_graphics_row(kernel):
    """Palette admission failure aborts its sole producer JSL before publication."""
    marker = bytes.fromhex('a9 ae b4 8f f0 3f 41')
    at = kernel.find(marker)
    if at < 0 or kernel.count(marker) != 1 or kernel[at + 7] != 0x4c:
        raise ValueError('WORKSPACE_GRAPHICS_ROW_FAULT_LAYOUT')
    # Discard exactly the row's three-byte JSL return. RTL then returns to
    # the cooperative executor, which owns the producer's outer call frame.
    return kernel[:at] + bytes.fromhex('a9 ae b4 8f d0 34 00 e2 20 a9 00 8f 30 22 00 c2 20 3b 18 69 03 00 1b 38 6b')
