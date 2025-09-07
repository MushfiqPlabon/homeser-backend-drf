#!/bin/bash
ts=$(date +"%Y%m%d_%H%M")
mkdir -p ~/homeserve_snapshots/$ts
git rev-parse --abbrev-ref HEAD > ~/homeserve_snapshots/$ts/branch.txt
git log -1 --pretty=format:"%h %s" > ~/homeserve_snapshots/$ts/lastcommit.txt
cp progress.txt ~/homeserve_snapshots/$ts/progress.txt
git bundle create ~/homeserve_snapshots/$ts/repo.bundle --all
zip -r ~/homeserve_snapshots/$ts/frontend_build.zip homeser-frontend-react/dist || true