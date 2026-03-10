#!/bin/bash
for f in $(find frontend/src -name "*.jsx" -o -name "*.tsx"); do
  if grep -q "<button" "$f"; then
    missing_aria=$(grep -B 2 -A 3 "<button" "$f" | grep -v "aria-label" | grep -v "aria-hidden" | grep "className" | grep "<[A-Z]" | grep -E "w-[0-9]+|h-[0-9]+")
    if [ ! -z "$missing_aria" ]; then
      echo "File: $f might have icon-only buttons missing aria-label"
    fi
  fi
done
