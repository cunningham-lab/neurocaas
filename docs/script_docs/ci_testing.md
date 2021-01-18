
Script documentation for file: ci_testing, Updated on:2020-12-18 11:23:07.754631
================================================================================

# Continuous Integration for Python Packages, Docker Containers and AWS Applications


This week (12/14), we spent a lot of effort in getting continuous integration up and running for our neurocaas contrib project. This was important because having ci streamlined will form the basis for our pull request based developer merging workflow. In particular, in our envisioned workflow, developers will 1) fork the neurocaas_contrib repo, 2) build their own application, 3) submit a pull request to merge their additions with the main neurocaas_contrib repo. Upon submission of this pull request, we will use ci based actions to automatically test the proposed analysis algorithm using localstack, and then build it on our AWS account. In the process, we figured out a few important features of package development and ci with services we care about (Docker Container, AWS Applications) too.
## Platform


The first thing that we had to do was switch over our CI testing platform from Travis CI to Github Actions. This was because Travis recently instituted a limit on the number of jobs an open source project can run on their platform for free. While reasonable this could be a major bottleneck to development, so we switched to Github Actions. It turns out this may have been a blessing in disguise, as Github Actions has been much easier to integrate with other services and potential workflows.
## Packaging and Data Files


The first roadblock I ran into when setting up CI testing was proper treatment of data files that were tied to a python package, in particular how to store them in a way where they could be referenced in code unambiguously. Because I package my source code independently of my tests, it's important to be careful about where certain data files go: in the tests folder, where they should be treated as user data, or in the source code, where they should be treated as internally referenced data that the user might never have access too (e.g. a default setting for a parameter in case it's not provided by the user). In the first case, we can always locate the test directory by calling the code:

```python
        fileloc = os.path.realpath(__file__)
```

The __file__ attribute will allow you to reference the file location unambiguously. There are some caveats: this attribute will not exist for certain code compiled from C (I think?) but we should not have to worry about that for these purposes

In the case that you are packaging data inside the source code of a python package, you have to be a little more careful. In these cases, depending on how users install the package (in edit mode or not, depending on the operating system), the data files will be installed in a different location. To account for this, we need to take two steps: 1) make sure that all directories containing data files are initialized as python packages (i.e. they have a `__init__.py` file). 2) set up your setup.py file so that setuptools.setup() has the following arguments  
``packages = setuptools.find_packages() # ensures that all subpackages of the main packages are discovered and included.``  
``include_package_data = True # ensures that non-python files can still be found.``  
``package_data={'package_name':['*.ext','example*.file']}``  
This last line deserves some explanation. The package_data parameter takes a dictionary, where the keys are packages where we should look for certain filetypes, and the values are lists of path fragments (wildcards okay) that should be included as package data. If the key given is blank, (""), setup tools will look through all packages and subpackages on setup. Note that all entries in the value list must be basenames: no paths that include directories are allowed (as packages don't work that way.)

These tools together should resolve the issue of relative paths in packages for good
## Docker Containers on CI


Although it seems like it could be complicated, it's actually fairly straightforward to setup docker on Github Actions. Docker has released a custom action to log in to docker hub (https://docs.docker.com/ci-cd/github-actions/) that uses Github repository secrets. From there you can use docker cli commands or the docker python sdk as you do on your local machine.
## Testing AWS Applications on CI


I am testing AWS applications on CI for this project using localstack. After logging in to docker hub in the previous step, you can easily set up localstack for testing by using the Github Actions service container feature (https://docs.github.com/en/free-pro-team@latest/actions/guides/about-service-containers). Because we just have to have the localstack container up and running to be able to test against it, we don't have to worry so much about configuration with environment variables, running in headless mode or other options (see neurocaas_contrib/.github/workflows/test_ci.yml for example). For an example where your application is itself running in a docker container and needs to reference the localstack container, see (https://github.com/merowareinstance/example-aws-services-github-worflows)