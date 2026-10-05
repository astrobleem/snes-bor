; Portable source spawn request, outside bank 0. This is request state only:
; model-name resolution and smartspawn/world allocation remain unbound.
; BOR 4086 clearspawnentry: memset zero, then index/itemindex/weaponindex=-1,
; *pretvar=NULL. Portable model identities use $FFFF for null model pointers.
; Supported request ABI fields; unimplemented setspawnentry properties fault.
VmSourceSpawn_Ready = $7FF67E      ; .dw $B4E1 initialized request, else absent
VmSourceSpawn_Entry = $7FF680      ; 64-byte owned request, zero defaults
VmSourceSpawn_Model = $7FF680      ; .dw stable source model ID, $FFFF null
VmSourceSpawn_ItemModel = $7FF682
VmSourceSpawn_Index = $7FF684      ; .dd -1 after clear
VmSourceSpawn_ItemIndex = $7FF688
VmSourceSpawn_WeaponIndex = $7FF68C
VmSourceSpawn_WeaponModel = $7FF690
VmSourceSpawn_Flags = $7FF692      ; .dw property-presence mask, initially zero
VmSourceSpawn_X = $7FF694          ; .dd Q16.16, ACCEPTED_COMPAT
VmSourceSpawn_A = $7FF698
VmSourceSpawn_Z = $7FF69C
VmSourceSpawn_Alpha = $7FF6A0      ; .dd
VmSourceSpawn_Map = $7FF6A4
VmSourceSpawn_Health = $7FF6A8     ; four .dd health overrides
VmSourceSpawn_Mp = $7FF6B8
VmSourceSpawn_Reserved = $7FF6BC   ; .dd zero, not an ignored source property
VM_SOURCE_SPAWN_BYTES = 64

Vm_SourceSpawnClear:
.a16
.i16
    lda.l VmCall_Argc
    and #$00FF
    beq Vm_SourceSpawnClear__clear
    sec
    lda #VMERR_BAD_NATIVE
    rtl
Vm_SourceSpawnClear__clear:
.a16
.i16
    ldx #0
    lda #0
Vm_SourceSpawnClear__zero:
.a16
.i16
    sta.l VmSourceSpawn_Entry,x
    inx
    inx
    cpx #VM_SOURCE_SPAWN_BYTES
    bcc Vm_SourceSpawnClear__zero
    lda #$FFFF
    sta.l VmSourceSpawn_Model
    sta.l VmSourceSpawn_ItemModel
    sta.l VmSourceSpawn_WeaponModel
    sta.l VmSourceSpawn_Index
    sta.l VmSourceSpawn_Index+2
    sta.l VmSourceSpawn_ItemIndex
    sta.l VmSourceSpawn_ItemIndex+2
    sta.l VmSourceSpawn_WeaponIndex
    sta.l VmSourceSpawn_WeaponIndex+2
    lda #$B4E1
    sta.l VmSourceSpawn_Ready
    jmp Vm_NativeVariantDispatch__null_ok ; complete EMPTY, not INTEGER zero
