#!/bin/bash
echo "Last progress:"
tail -n 40 progress.txt || true
echo ""
echo "Check latest commit:"
git log -1 --pretty=oneline || true
echo ""
echo "Open files referenced in progress.txt and resume work."