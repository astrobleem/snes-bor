"""Pinned 32-bit C loader direct integer assignment of GET_FLOAT_ARG*200.

The measured C implementation retains a double intermediate for this expression.
Do not insert a binary32 store before the integer conversion. Float model fields
which actually store a float use their separate binary32 loader path.
"""
import math

def ticks(value):
 product=float(value)*200
 if not math.isfinite(product):raise ValueError('SOURCE_INTEGER_TICKS_FINITE_REQUIRED')
 result=int(product)
 if not -2147483648<=result<=2147483647:raise ValueError('SOURCE_INTEGER_TICKS_INT32_REQUIRED')
 return result
