"""Pinned common_think ordered short-circuit owner; bodies are services."""
from enum import IntEnum
class Service(IntEnum):
    WARP=1
    LIE=2
    GRABBED=3
    GRAB=4
    ESCAPE=5
    BUSY=6
    ATTACK=7
    MOVE=8

def common_think(e):
    if e['dead']:return
    for service in Service:
        result=yield service
        if service!=Service.MOVE and result:return
