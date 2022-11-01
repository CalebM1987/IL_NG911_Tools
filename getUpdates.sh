#!/bin/bash
git fetch --all
git stash
git pull
echo "update successful, hit any key to exit"
pause