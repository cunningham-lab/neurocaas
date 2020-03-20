#!/bin/bash
## Script to handle path management in this package in a centralized way. 

## We want the paths to our three main code directories, then we're good. 
user_dir="user_profiles/__init__.py"
analysis_dir="ncap_blueprints/__init__.py"
utils_dir="utils/"


get_abs_filename() {
  # $1 : relative filename
  if [ -d "$(dirname "$1")" ]; then
    echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  fi
}

export userdir_absolute="$(dirname "$(get_abs_filename "$user_dir")")"
export analysisdir_absolute="$(dirname "$(get_abs_filename "$analysis_dir")")"
echo "creating environment variable $userdir_absolute for user profiles"
echo "creating environment variable $analysisdir_absolute for ncap blueprints"

