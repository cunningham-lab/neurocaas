# tests the dev_builder module that compiles cfn templates through cloudformation. 
from ncap_iac.utils import dev_builder
import pytest 
import os

loc = os.path.abspath(os.path.dirname(__file__))
test_mats = os.path.join(loc,"test_mats")

## TODO test against relative paths to lambda code. 
## TODO refactor init to inherit directly from NeuroCaaSTemplate with super. 

@pytest.mark.parametrize("postprocess,field,file",[(False,None,"end.txt"),(True,"SearchLambda","SeqLabel.json")])
def test_DevTemplate(postprocess,field,file): 
    if postprocess:
        config = "stack_config_template_posttrigger.json"
    else:    
        config = "stack_config_template.json"
    template = dev_builder.DevTemplate(os.path.join(test_mats,config))
    tdict = template.template.to_dict()
    print(tdict["Resources"].keys())
    if field is not None:
        assert tdict["Resources"].get(field,False)

    assert tdict["Resources"]["SearchLambda"]["Properties"]["Events"]["BucketEventnewgroupAnalysisEnd"]["Properties"]["Filter"]["S3Key"]["Rules"][1]["Value"] == file

def test_InitTemplate():        
    config = "stack_config_template.json"
    template = dev_builder.InitTemplate(os.path.join(test_mats,config))
    
@pytest.mark.parametrize("postprocess,field,file",[(False,None,"end.txt"),(True,"SearchLambda","SeqLabel.json")])
def test_WebDevTemplate(postprocess,field,file): 
    if postprocess:
        config = "stack_config_template_posttrigger.json"
    else:    
        config = "stack_config_template.json"
    template = dev_builder.WebDevTemplate(os.path.join(test_mats,config))
    tdict = template.template.to_dict()
    assert tdict["Resources"]["SearchLambda"]["Properties"]["Events"]["BucketEventnewgroupAnalysisEnd"]["Properties"]["Filter"]["S3Key"]["Rules"][1]["Value"] == file

@pytest.mark.parametrize("postprocess,field,file",[(False,None,"end.txt"),(True,"SearchLambda","SeqLabel.json")])
def test_WebSubstackTemplate(postprocess,field,file): 
    if postprocess:
        config = "stack_config_template_posttrigger.json"
    else:    
        config = "stack_config_template.json"
    template = dev_builder.WebSubstackTemplate(os.path.join(test_mats,config))
    tdict = template.template.to_dict()
<<<<<<< HEAD
    assert tdict["Resources"]["SearchLambda"]["Properties"]["Events"]["BucketEventAnalysisEnd"]["Properties"]["Filter"]["S3Key"]["Rules"][0]["Value"] == file
=======
    assert tdict["Resources"]["SearchLambda"]["Properties"]["Events"]["BucketEventnewgroupAnalysisEnd"]["Properties"]["Filter"]["S3Key"]["Rules"][1]["Value"] == file

def test_Dev_Template_Trunc():
    config = "stack_config_template.json"
    config_trunc = "stack_config_template_trunc.json"
    template = dev_builder.DevTemplate(os.path.join(test_mats,config))
    template_trunc = dev_builder.DevTemplate(os.path.join(test_mats,config_trunc))
    orig = template.config
    new = template_trunc.config
    for key in ["cwrolearn","figlambarn","figlambid"]:
        orig["Lambda"]["LambdaConfig"].pop(key)
        new["Lambda"]["LambdaConfig"].pop(key)
    assert template.config == template_trunc.config

def test_Init_Template_Trunc():
    config = "stack_config_template.json"
    config_trunc = "stack_config_template_trunc.json"
    template = dev_builder.InitTemplate(os.path.join(test_mats,config))
    template_trunc = dev_builder.InitTemplate(os.path.join(test_mats,config_trunc))
    assert template.config == template_trunc.config

def test_WebDev_Template_Trunc():
    config = "stack_config_template.json"
    config_trunc = "stack_config_template_trunc.json"
    template = dev_builder.WebDevTemplate(os.path.join(test_mats,config))
    template_trunc = dev_builder.WebDevTemplate(os.path.join(test_mats,config_trunc))
    orig = template.config
    new = template_trunc.config
    for key in ["cwrolearn","figlambarn","figlambid"]:
        orig["Lambda"]["LambdaConfig"].pop(key)
        new["Lambda"]["LambdaConfig"].pop(key)
    assert template.config == template_trunc.config

def test_WebSubstack_Template_Trunc():
    config = "stack_config_template.json"
    config_trunc = "stack_config_template_trunc.json"
    template = dev_builder.WebSubstackTemplate(os.path.join(test_mats,config))
    template_trunc = dev_builder.WebSubstackTemplate(os.path.join(test_mats,config_trunc))
    orig = template.config
    new = template_trunc.config
    for key in ["cwrolearn","figlambarn","figlambid"]:
        orig["Lambda"]["LambdaConfig"].pop(key)
        new["Lambda"]["LambdaConfig"].pop(key)
    assert template.config == template_trunc.config
>>>>>>> 9e631943ac68770a40b00088d9520fdbaefe4cd9
