#!/usr/bin/env bash
# scripts/check-instance-keys.sh — Reject raw `symbol_short!` storage keys in
# alert-registry; every storage access must go through `instance_key` (or DataKey).
set -euo pipefail

FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/contracts/alert-registry/src/lib.rs"

# Slurp the file so chained calls split over several lines are matched too.
# Any `.storage()` ... `.get/.set/.remove/.has/.extend_ttl(&symbol_short!(` is a violation.
# The `instance_key` module itself defines constants with `pub const`, never in
# a storage() call, so it is not affected.
if matches=$(perl -0777 -ne '
  while (/(\.storage\(\)(?:\s*\.\w+\(\))?\s*\.(?:get|set|remove|has|extend_ttl)(?:::<[^(]*>)?\(\s*&?symbol_short!\([^)]*\))/g) {
    print "$1\n";
  }' "$FILE") && [ -n "$matches" ]; then
  echo "Error: raw symbol_short! storage keys found in $FILE; use instance_key::*:" >&2
  echo "$matches" >&2
  exit 1
fi
echo "==> No raw symbol_short! storage keys found."
