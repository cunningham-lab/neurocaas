import setuptools

with open("README.md","r") as fh:
    long_description = fh.read()

setuptools.setup(
        name = "ncap_iac",
        version = "0.0.1",
        author = "Taiga Abe",
        author_email = "ta2507@columbia.edu",
        description = "Package distribution for the ncap project", 
        long_description = long_description,
        long_description_content_type = "test/markdown", 
        url = "https://github.com/cunningham-lab/ctn_lambda",
        packages = setuptools.find_packages(),
        classifiers = [
            "License :: OSI Approved :: MIT License"],
        python_requires=">3.6",
        )

