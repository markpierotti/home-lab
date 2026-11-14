#!/bin/bash
# Hermes scheduler owns the cadence; preserve failure status for its run receipt.
set -u
DIR="$HOME/Library/Application Support/SlimVaultMirror"
LOG="$DIR/launchd.log"
/bin/bash "$DIR/run-mirror.sh" >>"$LOG" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "Slim vault mirror failed (exit $rc). See ~/Library/Application Support/SlimVaultMirror/mirror-status.json"
fi
exit "$rc"
