#!/bin/bash

# Meta build script wrapper
# Runs all build tasks: categories generation and README build

cd "$(dirname "$0")/.." || exit 1

node scripts/build-all.js
