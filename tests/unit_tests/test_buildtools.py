"""
NOTE: Run all tests from inside the tests folder, as: 
    >>> pytest test_buildtools.py

Suite of tests for the bash script based- build tools that we have written.  
"""
import pytest
import os 
import subprocess

"""
Suite of tests to check that new pipelines are configured correctly using configure.sh 
"""

class ConstructBlueprintBase():
    """
    Abstract class for tests on constructing pipelines. Shares buildUp and tearDown methods to all relevant test classes.  
    """

    def tearDown(self,pathname):
        """
        Cleanup function: deletes the folder with given name after testing is done. 
        inputs:
        pathname (str): the relative name of the path where the test directory was created. 
        """
        os.remove(os.path.join(pathname,"stack_config_template.json"))
        os.rmdir(pathname)
        subprocess.call(["git","rm",pathname])

class ConstructProfileBase():
    """
    Abstract class for tests on constructing pipelines. Shares buildUp and tearDown methods to all relevant test classes.  
    """
    def tearDown(self,pathname):
        """
        Cleanup function: deletes the folder with given name after testing is done. 
        inputs:
        pathname (str): the relative name of the path where the test directory was created. 
        """
        os.remove(os.path.join(pathname,"user_config_template.json"))
        os.rmdir(pathname)

class TestConfigureBlueprint(ConstructBlueprintBase): 

    def test_basic_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a file name and run from the iac_utils directory.  
        """
        
        ## Create this folder 
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        self.pathname = "autogen_test_stack"
        currdir = os.getcwd()
        os.chdir("../ncap_blueprints/iac_utils")
        subprocess.call(["bash","configure.sh",self.pathname])
        assert os.path.exists(os.path.join("../",self.pathname))
        assert os.path.exists(os.path.join("../",self.pathname,"stack_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../ncap_blueprints",self.pathname))

    def test_ncap_blueprints_paths_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a file name and run from the ncap_blueprints directory  
        """
        ## Create this folder 
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        self.pathname = "autogen_test_stack_blueprint"
        ## Try with ncap_blueprints:
        currdir = os.getcwd()
        os.chdir("../ncap_blueprints")
        subprocess.call(["bash","iac_utils/configure.sh",self.pathname])
        assert os.path.exists(self.pathname)
        assert os.path.exists(os.path.join(self.pathname,"stack_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../ncap_blueprints",self.pathname))

    def test_ncap_iac_paths_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a file name and run from the ncap_iac directory.  
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        ## Create this folder 
        self.pathname = "autogen_test_stack_iac"
        ## Try with ncap_iac
        currdir = os.getcwd()
        os.chdir("../")
        subprocess.call(["bash","ncap_blueprints/iac_utils/configure.sh",self.pathname])
        assert os.path.exists(os.path.join("ncap_blueprints/",self.pathname))
        assert os.path.exists(os.path.join("ncap_blueprints/",self.pathname,"stack_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../ncap_blueprints",self.pathname))

    def test_ncap_pipeline_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a file name and run from the ncap_iac directory.  
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        ## Create this folder 
        self.pathname = "autogen_test_stack_pipeline"
        ## Make one:
        currdir = os.getcwd()
        os.chdir("../")
        subprocess.call(["bash","ncap_blueprints/iac_utils/configure.sh",self.pathname])
        assert os.path.exists(os.path.join("ncap_blueprints/",self.pathname))
        assert os.path.exists(os.path.join("ncap_blueprints/",self.pathname,"stack_config_template.json"))
        os.chdir(os.path.join("ncap_blueprints/",self.pathname))
        
        ## Try from inside another pipeline folder. 
        self.pathname2 = "autogen_2_test_stack_blueprint"
        subprocess.call(["bash","../iac_utils/configure.sh",self.pathname2])
        assert os.path.exists(os.path.join("../",self.pathname2))
        assert os.path.exists(os.path.join("../",self.pathname2,"stack_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../ncap_blueprints",self.pathname))
        self.tearDown(os.path.join("../ncap_blueprints",self.pathname2))

class TestConfigureProfile(ConstructProfileBase): 

    def test_basic_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a valid file name and run from the iac_utils directory.  
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        ## Create this folder 
        self.pathname = "autogen-test-users"
        currdir = os.getcwd()
        os.chdir("../user_profiles/iac_utils")
        subprocess.call(["bash","configure.sh",self.pathname])
        assert os.path.exists(os.path.join("../",self.pathname))
        assert os.path.exists(os.path.join("../",self.pathname,"user_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../user_profiles",self.pathname))

    def test_user_profiles_paths_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a valid file name and run from the user_profiles directory  
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        ## Create this folder 
        self.pathname = "autogen-test-users-profile"
        ## Try with user_profiles:
        currdir = os.getcwd()
        os.chdir("../user_profiles")
        subprocess.call(["bash","iac_utils/configure.sh",self.pathname])
        assert os.path.exists(self.pathname)
        assert os.path.exists(os.path.join(self.pathname,"user_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../user_profiles",self.pathname))

    def test_ncap_iac_paths_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a valid file name and run from the ncap_iac directory.  
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        ## Create this folder 
        self.pathname = "autogen-test-users-iac"
        ## Try with ncap_iac
        currdir = os.getcwd()
        os.chdir("../")
        subprocess.call(["bash","user_profiles/iac_utils/configure.sh",self.pathname])
        assert os.path.exists(os.path.join("user_profiles/",self.pathname))
        assert os.path.exists(os.path.join("user_profiles/",self.pathname,"user_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../user_profiles",self.pathname))

    def test_ncap_pipeline_configure(self,pytestconfig):
        """
        Test the basic functionality of configure.sh given a valid file name and run from another pipeline directory.  
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        ## Create this folder 
        self.pathname = "autogen-test-users-pipeline"
        ## Make one:
        currdir = os.getcwd()
        os.chdir("../")
        subprocess.call(["bash","user_profiles/iac_utils/configure.sh",self.pathname])
        assert os.path.exists(os.path.join("user_profiles/",self.pathname))
        assert os.path.exists(os.path.join("user_profiles/",self.pathname,"user_config_template.json"))
        os.chdir(os.path.join("user_profiles/",self.pathname))
        
        ## Try from inside another pipeline folder. 
        self.pathname2 = "autogen-2-test-users-pipeline"
        subprocess.call(["bash","../iac_utils/configure.sh",self.pathname2])
        assert os.path.exists(os.path.join("../",self.pathname2))
        assert os.path.exists(os.path.join("../",self.pathname2,"user_config_template.json"))
        os.chdir(currdir)
        self.tearDown(os.path.join("../user_profiles",self.pathname))
        self.tearDown(os.path.join("../user_profiles",self.pathname2))

    def test_name_underscores(self,pytestconfig,capfd):
        """
        Test that we're correctly catching incorrectly configured paths (no underscores. )
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        self.pathname = "autogen_test_users_iac"
        ## Try with ncap_iac
        currdir = os.getcwd()
        os.chdir("../")
        subprocess.call(["bash","user_profiles/iac_utils/configure.sh",self.pathname])
        captured = capfd.readouterr()
        assert captured.err.split("\n")[3] == "AssertionError: Names must be alphanumeric"
        os.chdir(currdir)
        
    def test_name_uppercase(self,pytestconfig,capfd):
        """
        Test that we're correctly catching incorrectly configured paths (no underscores. )
        """
        os.chdir(os.path.join(pytestconfig.rootdir,"ncap_iac/tests/"))
        self.pathname = "Autogen-test-users-iac"
        ## Try with ncap_iac
        currdir = os.getcwd()
        os.chdir("../")
        subprocess.call(["bash","user_profiles/iac_utils/configure.sh",self.pathname])
        captured = capfd.readouterr()
        assert captured.err.split("\n")[3] == "AssertionError: Names must be alphanumeric"
        os.chdir(currdir)
