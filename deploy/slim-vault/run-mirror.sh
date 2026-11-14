#!/bin/bash
# One bounded scheduled pull. iCloud receiver files are not read for delta checks.
set -u
DIR="$HOME/Library/Application Support/SlimVaultMirror"
cd "$DIR" || exit 1
exec /usr/bin/python3 "$DIR/mirror.py" "$@"
