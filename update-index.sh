#!/bin/bash

# Navigate to the script directory and run the build-readme script
cd "$(dirname "$0")/private/scripts"
node build-readme.js
