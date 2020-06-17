import sys
import os
import json 
import itertools
import csv
import pathlib
current_dir = pathlib.Path(__file__).parent.absolute()
## Tools to automatically fill in user stack templates from csvs. 
## We need a tool to parse excel files -> dictionary. 
## We need a tool to validate and separate out users into valid and invalid entries, and reprint that. 
## We need a tool to take dictionary, and append it to an existing user template. 
## We need a tool to look at that appended template and make sure it's okay.

def get_user_dict(header,row):
    ## Function to be curried and fed into map.  
    return {h:row[hi] for hi,h in enumerate(header)}

def filter_verified(userdict):
    ## Convert type
    intverified = userdict['Verified']
    ## Function to be curried and fed into map.
    ## Passed from csv as a string. 
    if intverified == '1':
        verified = True 
    else:
        verified = False 
    return verified 

def identify_groups(userdict):
    group = userdict['Affiliation']
    return group

def convert_dict_to_json_individual(userdict,pipelines = "all"):
    # Assume a dict of the form given by processing csv, and output a dictionary of the form expected for json.  
    username = userdict['Email'].split('@')[0]
    if pipelines == "all":
        pipelines = ['caiman_web_stack','dlc_web_stack','epi_web_stack','pmd_web_stack','locanmf_web_stack']
    elif type(pipelines) == list:
        pass
    else:
        raise TypeError("pipelines should be list of names of folders in ncap_blueprints.")
    jsondict = {"AffiliateName":'{}group'.format(username),'UserNames':[username],'ContactEmail':{username:userdict['Email']},'Pipelines':pipelines,"PipelineDir":'things are fine here'}
    return jsondict

def convert_dict_to_json_group(userdicts,pipelines = 'all'):
    assert type(userdicts) == list, 'convert iterator to list before passing here.'
    if pipelines == "all":
        pipelines = ['caiman_web_stack','dlc_web_stack','epi_web_stack','pmd_web_stack','locanmf_web_stack']
    elif type(pipelines) == list:
        pass
    else:
        raise TypeError("pipelines should be list of names of folders in ncap_blueprints.")
    ## Now we are going to assume the affiliation of everyone here is the same group. 
    groupname = userdicts[0]['Affiliation']
    assert [udict['Affiliation'] == groupname for udict in userdicts], 'make sure grouping worked.'
    emails = {udict['Email'].split('@')[0]:udict['Email'] for udict in userdicts}
    usernames = [uemail.split('@')[0] for uemail in emails]
    
    jsondict = {'AffiliateName':groupname,'UserNames':usernames,'ContactEmail':emails,'Pipelines':pipelines,'PipelineDir':'not in use'}
    
    return jsondict

def parse_userfile(path):
    """
    Take the path to the user file, and crete a two dictionaries: 1. valid users, with usernames, emails, and affiliations. 
    2. invalidated users, who should be sent an email requesting id confirmation. 
    """
    with open(path,"r",newline='') as datafile: 
        datareader = csv.reader(datafile,dialect="excel")
        ## Assume the first row is a header row. 
        header = next(datareader)
        assert header == ['Email','FirstName','LastName','Affiliation','Verified','Loaded'], 'header must have correct format.'
        dictfunc_parametrized = lambda reader: get_user_dict(header,reader)

        ## Get data dictionaries: 
        datadicts = map(dictfunc_parametrized,datareader)

        ## Sort by if the users are verified: 
        datadicts_sorted = sorted(datadicts,key = filter_verified)

        ## Now group:
        datadicts_verified = itertools.groupby(datadicts_sorted,filter_verified)

        ## Workflow splits based on if the datasets are verified or not:
        verifiedlist = []
        for key,group in datadicts_verified:
            if key is True:
                sortedby_group = sorted(group,key = identify_groups) 
                datadicts_sorted = itertools.groupby(sortedby_group,identify_groups)
                for groupname, grouped in datadicts_sorted:
                    print(groupname)
                    if groupname == "Website":
                        dictvals = list(map(convert_dict_to_json_individual,grouped))
                        print(dictvals,'WebsiteDictvals')
                        verifiedlist = verifiedlist+dictvals
                    else:
                        dictval = convert_dict_to_json_group(list(grouped))
                        verifiedlist.append(dictval)
            elif key is False:
                unverifiedlist = list(group)
            else: 
                raise Exception("unexpected key.")

    return verifiedlist,unverifiedlist
        
def get_usertemplate():
    path = os.path.join(os.path.dirname(current_dir),"user_config_template.json")
    with open(path,'r') as f:
        config = json.load(f)
    return config

def write_usertemplate(grouppath,writtenconfig):
    '''
    We want to make sure we are not overwriting something. Only execute write if it looks like this is new. 
    '''
    path = os.path.join(grouppath,'user_config_template.json')
    with open(path,'r') as f:
        config = json.load(f)
    ## Make sure we're not overwriting. 
    assert config['UXData']['Affiliates'][0]['AffiliateName'] == "Affiliate's Name here. Must follow S3 bucket name conventions."
    assert len(config['UXData']['Affiliates']) == 1
    with open(path,'w') as f:
        json.dump(writtenconfig,fp = f,indent = 4)
    

if __name__ == "__main__":
    csvpath = sys.argv[1]
    grouppath = sys.argv[2]
    ## Get lists of verified and unverified users, correctly formatted, from list
    verifiedlist, unverifiedlist = parse_userfile(csvpath)
    config = get_usertemplate()
    config['UXData']['Affiliates'] = verifiedlist
    ## TODO: Check for username uniqueness within the template.
    ## TODO: Check for groupname uniqueness. 
    ## TODO: Check for groupname validity. 
    ## TODO: check for user existence here. 
    write_usertemplate(grouppath,config)


    
