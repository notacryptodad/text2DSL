import os
import re

files = [
    "frontend/src/components/AnnotationEditor.jsx",
]

for filepath in files:
    with open(filepath, 'r') as f:
        content = f.read()

    # We will search for button elements that contain just an X icon and lack aria-label
    # It's better to do this manually in replacing
