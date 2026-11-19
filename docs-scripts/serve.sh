#!/bin/sh
set -eu

cd "$(dirname "$0")/../docs"
exec python3 -m http.server 9000 --bind 0.0.0.0
