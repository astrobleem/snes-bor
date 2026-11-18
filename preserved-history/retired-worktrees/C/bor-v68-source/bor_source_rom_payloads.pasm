; 708 authenticated immutable source blocks in previously unused ROM space.
.bank 52
.org $8000
SourceRom_Ids:
    .incbin "bor_rom_block_ids.bin"
SourceRom_PayloadBanks:
    .dw $35,$36,$37,$3A,$3B,$3C
.bank 53
.org $8000
SourceRom_Payload35:
    .incbin "bor_rom_payload_35.bin"
.bank 54
.org $8000
SourceRom_Payload36:
    .incbin "bor_rom_payload_36.bin"
.bank 55
.org $8000
SourceRom_Payload37:
    .incbin "bor_rom_payload_37.bin"
.bank 58
.org $8000
SourceRom_Payload3A:
    .incbin "bor_rom_payload_3a.bin"
.bank 59
.org $8000
SourceRom_Payload3B:
    .incbin "bor_rom_payload_3b.bin"
.bank 60
.org $8000
SourceRom_Payload3C:
    .incbin "bor_rom_payload_3c.bin"
.bank 56
.org $8000
SourceRom_Dense38:
    .incbin "bor_rom_dense_38.bin"
.bank 57
.org $8000
SourceRom_Dense39:
    .incbin "bor_rom_dense_39.bin"
