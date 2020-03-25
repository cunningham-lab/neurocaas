import sys
import re

if __name__ == "__main__":
    string = sys.argv[1]

    valid = re.match("^[a-z0-9\-]+$",string) is not None
    assert valid, "Names must be alphanumeric"
