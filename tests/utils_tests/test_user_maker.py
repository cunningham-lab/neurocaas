### Test suite for user maker tools using cloudformation. 
from ncap_iac.utils import user_maker 
import pytest
import os

loc = os.path.abspath(os.path.dirname(__file__))
test_mats = os.path.join(loc,"test_mats")

def mockdeploy(template):
    pass
    

def test_ReferenceUserCreationTemplate():
    utemp = user_maker.ReferenceUserCreationTemplate()


