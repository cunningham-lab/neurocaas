

def return_json_read(): 
    """ Returns the value of "caiman-ncap-web/columbianeurotheory/submissions/submit.json" as of 7/6/20. Returns as a utf-8 encoded string. 
    
    :return: utf-8 encoded string representing json output.  
    :rtype: bytes
    """
    return b'{"dataname": ["columbianeurotheory/inputs/images_YST.zip"], "configname": "columbianeurotheory/configs/NeuroCAAS_CaImAn_template_YST.yaml", "timestamp": "1592228201"}'

def return_json_malformed():
    """ Returns the value of return_json_read, but misformatted. 

    :return: utf-8 encoded string representing malformed json output. 
    :rtype: bytes

    """
    return b'{"dataname" ["columbianeurotheory/inputs/images_YST.zip"], "configname": "columbianeurotheory/configs/NeuroCAAS_CaImAn_template_YST.yaml", "timestamp": "1592228201"}'

def return_yaml_read(): 
    """ Returns the value of "caiman-ncap-web/columbianeurotheory/submissions/submit.yaml" as of 7/6/20. Returns as a utf-8 encoded string. 
    
    :return: utf-8 encoded string representing yaml output.  
    :rtype: bytes
    """
    return b"configname: columbianeurotheory/configs/NeuroCAAS_CaImAn_template_YST.yaml\ndataname:\n- columbianeurotheory/inputs/images_YST.zip\ntimestamp: '1592228201'\n" 

def return_yaml_malformed():
    """ Returns the value of return_yaml_read, but misformatted. 

    :return: utf-8 encoded string representing malformed yaml output. 
    :rtype: bytes

    """
    return b"configname columbianeurotheory/configs/NeuroCAAS_CaImAn_template_YST.yaml\ndataname:\n- columbianeurotheory/inputs/images_YST.zip\ntimestamp: '1592228201'\n" 

def return_tempdir_path():
    """ Returns the path to the temporary directory. 

    :return: path to temp base directory. 
    :rtype: str
    """
    return "fixture_dir/"
