#!/bin/bash

# Navigate to the script directory and run the build-readme script
cd "$(dirname "$0")/scripts"
node build-readme.js
