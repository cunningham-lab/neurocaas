from unittest.mock import MagicMock

### Make a mock s3 bucket with two dummy path variables.
#def make_mock_bucket():
#    mock_stored_obj_attrs = {"key":"key/key/key"}
#    mock_stored_obj = MagicMock(**mock_stored_obj_attrs) 
#    mocks3collection = MagicMock()
#    mocks3collection.__iter__.return_value = [mock_stored_obj,mock_stored_obj]
#    mock_bucket_attrs = {'objects.filter.return_value':mocks3collection}
#    mock_bucket = MagicMock(**mock_bucket_attrs)
#    return mock_bucket

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
   
    filter_specs = [m for m in mock_obj_specs if filter_path in m["key"]]
    ## Now initialize a set of MagicMock objects: (later we might change this to be S3 object mocks created indepedently in a separate function)
    mock_stored_obj_list = [MagicMock(**m) for m in mock_obj_specs]
    filter_stored_obj_list = [MagicMock(**m) for m in filter_specs]

    ## Now initialize two s3 collections: like lists with extra methods. One for filter, one for full. 
    mock_s3collection_full = MagicMock()
    mock_s3collection_filter = MagicMock()
    ## Assign their return values. 
    print(filter_stored_obj_list)
    mock_s3collection_full.__iter__.return_value = mock_stored_obj_list
    mock_s3collection_filter.__iter__.return_value = filter_stored_obj_list
    mock_bucket_attrs = {
            'objects.filter.return_value':mock_s3collection_filter,
            'objects.all.return_value':mock_s3collection_full
            }
    mock_bucket = MagicMock(**mock_bucket_attrs)
    return mock_bucket

    
## Provide list of dicts for each object. 

## Provide path that you want to filter with (optional)

## Mock object (set content. )


## Mock client (for copy)

