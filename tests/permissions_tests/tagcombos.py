## Define the different tag sets you can use:
wrong_tags = [
                {
                    "ResourceType":"instance",
                    "Tags":[
                    {
                        "Key":"a",
                        "Value": "b"
                    },
                    ]
                }
             ] 
right_tags = [
                {
                    "ResourceType":"volume",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "On"
                    },
                    {
                        "Key":"Timeout",
                        "Value":"6",
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":"arn:aws:iam::739988523141:user/ta",
                    }
                    ]
                },
                {
                    "ResourceType":"instance",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "On"
                    },
                    {
                        "Key":"Timeout",
                        "Value":"6",
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":"arn:aws:iam::739988523141:user/ta",
                    }
                    ]
                }
             ] 

right_tags_instance_only = [
                {
                    "ResourceType":"instance",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "On"
                    },
                    {
                        "Key":"Timeout",
                        "Value":"6",
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":"arn:aws:iam::739988523141:user/ta",
                    }
                    ]
                }
             ] 

right_tags_volume_only = [
                {
                    "ResourceType":"volume",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "On"
                    },
                    {
                        "Key":"Timeout",
                        "Value":"6",
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":"arn:aws:iam::739988523141:user/ta",
                    }
                    ]
                }
             ] 

right_tags_wrong_val = [
                {
                    "ResourceType":"volume",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "Ox"
                    },
                    {
                        "Key":"Timeout",
                        "Value":"6",
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":"arn:aws:iam::739988523141:user/ta",
                    }
                    ]
                }
             ] 

right_tags_wrong_val = [
                {
                    "ResourceType":"volume",
                    "Tags":[
                    {
                        "Key":"PriceTracking",
                        "Value": "Ox"
                    },
                    {
                        "Key":"Timeout",
                        "Value":"6",
                    },
                    {
                        "Key":"OwnerArn",
                        "Value":"arn:aws:iam::739988523141:user/ta",
                    }
                    ]
                }
             ]
