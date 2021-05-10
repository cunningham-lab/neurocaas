import os

def get_context():
    homedir = os.environ["HOME"]
    if homedir == "/Users/taigaabe":
        scriptflag = "local"
    else:
        scriptflag = "ci"
    return scriptflag
