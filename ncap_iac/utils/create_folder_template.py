from user_maker import ReferenceFolderSubstackTemplate


with open("tmp_user_dir/template.json","w") as f:
    print(ReferenceFolderSubstackTemplate().template.to_json(),file = f)
