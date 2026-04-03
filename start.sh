#!/bin/bash
set -a
source "$(dirname "$0")/.env"
set +a
exec claude --plugin-dir "$(dirname "$0")"
