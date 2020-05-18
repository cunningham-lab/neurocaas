#!/bin/bash
set -e
## Coordinates test of generating experiment figures. 

source "$(dirname $0)"/paths.sh

rootpath=$(dirname $(dirname $(get_abs_filename "$0" )))
cd $rootpath/experiments/

python recreate_figure4.py

