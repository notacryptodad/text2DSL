import os
import re

# We will recursively walk over all .jsx files in frontend/src
# and check for <button elements that contain an <X or <Trash etc without aria-label

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Match <button> tags that only contain an icon or simple SVG, lacking aria-label
    # Regex is tricky for nested HTML. Let's do string search.
    pass
