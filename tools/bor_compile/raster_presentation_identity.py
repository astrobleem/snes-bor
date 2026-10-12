"""Bind a compiled schedule and source-exact math controls in one digest."""
import hashlib
import json


def refresh_presentation_identity(frame):
    fields=('compiled_schedule_sha256','selected_modes',
            'compiled_color_window_descriptors','source_rgb555_sha256')
    previous=frame.pop('compiled_presentation_sha256',None)
    if previous is not None:frame['input_compiled_presentation_sha256']=previous
    if not all(key in frame for key in fields):return
    payload=dict(schedule_sha256=frame['compiled_schedule_sha256'],
        selected_modes=frame['selected_modes'],
        compiled_color_window_descriptors=frame['compiled_color_window_descriptors'],
        source_rgb555_sha256=frame['source_rgb555_sha256'])
    frame['compiled_presentation_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
