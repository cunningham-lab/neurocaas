## tests the dev_builder module that compiles cfn templates through cloudformation. 
from ncap_iac.utils import dev_builder
import pytest 
import os

loc = os.path.abspath(os.path.dirname(__file__))
test_mats = os.path.join(loc,"test_mats")

## TODO test against relative paths to lambda code. 
## TODO refactor init to inherit directly from NeuroCaaSTemplate with super. 

@pytest.mark.parametrize("postprocess,field",[(False,None),(True,"SearchLambda")])
def test_DevTemplate(postprocess,field): 
    if postprocess:
        config = "stack_config_post_template.json"
    else:    
        config = "stack_config_template.json"
    template = dev_builder.DevTemplate(os.path.join(test_mats,config))
    tdict = template.template.to_dict()
    print(tdict["Resources"].keys())
    if field is not None:
        assert tdict["Resources"].get(field,False)
    
def test_WebDevTemplate(): 
    config = "stack_config_template.json"
    template = dev_builder.WebDevTemplate(os.path.join(test_mats,config))

def test_WebSubstackTemplate(): 
    config = "stack_config_template.json"
    template = dev_builder.WebSubstackTemplate(os.path.join(test_mats,config))
