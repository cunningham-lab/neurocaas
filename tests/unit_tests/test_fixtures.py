

def return_json_read(): 
    """ Returns the value of "caiman-ncap-web/columbianeurotheory/submissions/submit.json" as of 7/6/20. Returns as a utf-8 encoded string. 
    
    :return: utf-8 encoded string representing json output.  
    :rtype: bytes
    """
    return b'{"dataname": ["columbianeurotheory/inputs/images_YST.zip"], "configname": "columbianeurotheory/configs/NeuroCAAS_CaImAn_template_YST.yaml", "timestamp": "1592228201"}'

def return_json_malformed():
    """ Returns t he value of return_json_read, but misformatted. 

    :return: utf-8 encoded string representing malformed json output. 
    :rtype: bytes

    """
    return b'{"dataname" ["columbianeurotheory/inputs/images_YST.zip"], "configname": "columbianeurotheory/configs/NeuroCAAS_CaImAn_template_YST.yaml", "timestamp": "1592228201"}'

