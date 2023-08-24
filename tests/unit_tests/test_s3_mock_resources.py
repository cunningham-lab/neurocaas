from unittest.mock import MagicMock

## Full mock bucket: 
def make_mock_bucket(mock_obj_specs,filter_path = None):
    """ A function to return a mock S3 bucket, emulating the return value of an s3_resource.Bucket call. 

    :param mock_obj_specs: A list of dictionaries providing the attributes of each stored object. 
    :type mock_obj_specs: list
    :param filter_path: a path prefix that will be used to provide a way to select only a subset of mock objects. 
    :type filter_path: str, optional
    :return: mock_bucket
    :rtype: MagicMock
    """
    # Parameter validation
    assert all([type(mock_obj_name) == dict for mock_obj_name in mock_obj_specs]), "object specifications should be dictionaries"
    try:
        for m in mock_obj_specs:
            m["key"]
    except KeyError:
        print("object does not have necessary parameter 'key'")
        raise(KeyError("object does not have necessary parameter 'key'"))
   
    filter_specs = [m for m in mock_obj_specs if m["key"].startswith(filter_path)]
    ## Now initialize a set of MagicMock objects: (later we might change this to be S3 object mocks created independently in a separate function)
    mock_stored_obj_list = [make_mock_object(m) for m in mock_obj_specs]
    filter_stored_obj_list = [make_mock_object(m) for m in filter_specs]

    ## Now initialize two s3 collections: like lists with extra methods. One for filter, one for full. 
    mock_s3collection_full = MagicMock()
    mock_s3collection_filter = MagicMock()
    mock_s3collection_full.__iter__.return_value = mock_stored_obj_list
    mock_s3collection_filter.__iter__.return_value = filter_stored_obj_list
    mock_bucket_attrs = {
            'objects.filter.return_value':mock_s3collection_filter,
            'objects.all.return_value':mock_s3collection_full
            }
    mock_bucket = MagicMock(**mock_bucket_attrs)
    return mock_bucket

    
## Mock object (set content. )
def make_mock_object(specdict):
    """make_mock_object.

    :param keyname: the name of the key you want to associate with this object. 
    """
    mockobject = MagicMock(**specdict)
    #mockobject.delete = MagicMock(return_value = None)
    return mockobject


## Mock client (for copy)
def make_mock_file_object(bytesobj):
    """make_mock_file_object.

    :param bytesobj: the payload that will be delivered by the mock object. 
    :type bytesobj: bytes

    :return: mock object that can be queried for bytes input just as an s3 object can. 
    :rtype: MagicMock
    """
    bodymock = MagicMock()
    bodymock.read.return_value = bytesobj
    bodydict = {"Body":bodymock}
    mock_fileobj = MagicMock()
    mock_fileobj.get.return_value = bodydict
    file_object_attrs = {'get.return_value':{'Body':bodymock}}
    file_object_mock = MagicMock(**file_object_attrs)


    return mock_fileobj

