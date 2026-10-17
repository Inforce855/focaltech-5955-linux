#!/usr/bin/env bash
# Run the locally built libfprint example, keeping biometric files private.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
bld="$HOME/Projects/libfprint-ft5955-build"
priv="$root/local-data/libfprint-live"
[[ -x "$bld/examples/enroll" ]] || {
  echo "Missing $bld/examples/enroll; build isolated libfprint first." >&2
  exit 2
}
if [[ -L "$priv" ]]; then
  echo "Refusing symlinked private directory" >&2; exit 2
fi
umask 077
mkdir -p -- "$priv"
chmod 700 -- "$priv"
export FP_VIRTUAL_IMAGE="$priv/fingerprint.sock"
export FP_DRIVERS_WHITELIST=virtual_image
export LD_LIBRARY_PATH="$bld/libfprint${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd -- "$priv"
echo "Isolated libfprint enrolment: $FP_VIRTUAL_IMAGE"
echo "Start the bridge in a SECOND terminal when prompted to scan your finger."
echo "This upstream example can save enrolled.pgm and test-storage.variant in this private folder."
echo "No changes to Nobara's system fprintd or PAM."
exec "$bld/examples/enroll"
