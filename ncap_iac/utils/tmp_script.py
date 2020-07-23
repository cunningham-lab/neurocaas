import os 
import json
import sys
from user_maker import ReferenceUserCreationTemplate


filename = "../user_profiles/test-new-userorg/user_config_template.json"


template = ReferenceUserCreationTemplate(filename)
with open("tmp_user_dir/tmp_compiled.json","w") as f:
    print(template.template.to_json(),file = f)
