; Relocated unchanged from nearly full bank28. Every reader uses long loads.
; 16-byte records: length, 13 name bytes, source-record offset, expected tag.
Vm_SourceEntityNames:
    .db 1,"a",0,0,0,0,0,0,0,0,0,0,0,0,8,2
    .db 11,"animationid",0,0,16,1
    .db 9,"direction",0,0,0,0,24,1
    .db 6,"health",0,0,0,0,0,0,0,32,1
    .db 11,"playerindex",0,0,40,1
    .db 1,"x",0,0,0,0,0,0,0,0,0,0,0,0,48,2
    .db 1,"z",0,0,0,0,0,0,0,0,0,0,0,0,56,2
    .db 1,"y",0,0,0,0,0,0,0,0,0,0,0,0,8,2
    .db 7,"animnum",0,0,0,0,0,0,16,1
    .db 9,"maxhealth",0,0,0,0,64,1
