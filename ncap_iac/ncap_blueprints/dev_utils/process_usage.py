### File to process the number of monthly active users on neurocaas. 
import numpy as np
import json

def get_data(filename):
    with open(filename,"r") as f:
        d = json.load(f)

    return d

def sort_by_users(data):
    """
    take data sorted by analysis, and sort by users. 
    """
    # Get usernames:
    users = []
    for analysis in data.keys():
        analysisusers = data[analysis]["users"].keys()
        users += analysisusers
    unique_users = list(set(users))
    usercentric = {u:{"analyses":{}} for u in unique_users}
    for analysis in data:
        analysisusers = data[analysis]["users"].keys()
        for user in analysisusers:
            usage = data[analysis]["users"][user]
            usercentric[user]["analyses"][analysis] = usage 
            use_months = []
            for monthly_duration in usage["duration"]:
                if usage["duration"][monthly_duration] > 0:
                    use_months.append(monthly_duration)
            usercentric[user]["use_months"] = use_months

    return usercentric

def sort_by_month(sorted_by_users):
    """
    get n users per month. 
    """
    months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    monthly = {m:[] for m in months}
    monthly_usage = {m:[] for m in months}
    sorted_by_users.pop("reviewers",None)
    sorted_by_users.pop("sawtelllabdlcdevelop",None)
    sorted_by_users.pop("sawtelllab",None)
    for user in sorted_by_users:
        for use_month in sorted_by_users[user]["use_months"]:
            for a in sorted_by_users[user]["analyses"]:
                print(sorted_by_users[user]["analyses"][a]["cost"])
                data = sorted_by_users[user]["analyses"][a]["cost"][use_month]
                monthly_usage[use_month].append(data)
            monthly[use_month].append(user)
    return monthly,monthly_usage
    






if __name__  == "__main__":
    filename = "./neurocaas_activity.json"
    data = get_data(filename) 
    sorted_by_users = sort_by_users(data)
    users_by_month,usage_by_month = sort_by_month(sorted_by_users)
    for m in usage_by_month:
        ## Account for sawtell lab bug: replace thousands with 14 hrs for 2 x 70 videos.  
        if m == "August":
            usage_by_month[m].append(14)

        print(usage_by_month[m])
        print(np.mean(usage_by_month[m]))


