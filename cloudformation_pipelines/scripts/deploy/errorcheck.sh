#!/bin/bash

### Function to set the behavior of the embedded script. Defaults to exit upon encountering errors and to write out the last output we would have seen. 
function errorhandle {
    set -e 

    ## Get the last command for debugging.
    trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
    # echo an error message before exiting
    trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT
}
