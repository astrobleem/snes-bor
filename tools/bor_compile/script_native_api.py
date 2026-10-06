"""Stable generic source-VM API identities, independent of model/module order.

The native runtime binds entries individually. A declared ID is a required
capability, never evidence that its engine implementation exists.
"""
SIGNATURES=[('NULL',0),('changeentityproperty',3),('changeentityproperty',4),
    ('changeentityproperty',5),('checkwall',2),('clearlocalvar',0),('clearspawnentry',0),
    ('findtarget',1),('getentityproperty',2),('getlocalvar',1),('killentity',1),
    ('openborconstant',1),('performattack',2),('playerkeys',3),('projectile',8),
    ('rand',0),('setlocalvar',2),('setspawnentry',2),('spawn',0),('tossentity',4),('updateframe',2),
    ('tossentity',1),('tossentity',2),('tossentity',3)]
IDS={signature:0x200+index for index,signature in enumerate(SIGNATURES)}
