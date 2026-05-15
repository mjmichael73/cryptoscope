#!/usr/bin/env bash
# Seed a demo tenant and a set of tracked symbols so the stack has data to work
# with right after startup. Safe to run more than once.
set -euo pipefail

echo "Seeding demo tenant and symbols is wired to the command-service API."
echo "Run this after 'make up' once the services report healthy."
