from unittest.mock import MagicMock

## Make a mock s3 bucket with two dummy path variables.
def make_mock_bucket():
    mock_stored_obj_attrs = {"key":"key/key/key"}
    mock_stored_obj = MagicMock(**mock_stored_obj_attrs) 
    mocks3collection = MagicMock()
    mocks3collection.__iter__.return_value = [mock_stored_obj,mock_stored_obj]
    mock_bucket_attrs = {'objects.filter.return_value':mocks3collection}
    mock_bucket = MagicMock(**mock_bucket_attrs)
    return mock_bucket

## Full mock bucket: 
## Provide list of dicts for each object. 
## Provide path that you want to filter with (optional)

## Mock object (set content. )


## Mock client (for copy)

