# Introduction

### Welcome to NeuroCAAS! Thank you for considering contributing to the platform.

### Following these guidelines can help all members of our open source community work together productively. By following these guidelines, you save the developers of this project time, and in return, they should address your issues and changes.

### Please note that developers of data analysis algorithms who would like to contribute their analyses to NeuroCAAS should not contribute directly to this repo. Instead, they should read the [developer guide](docs/devguide.md). This guide is for developers who would like to contribute to the NeuroCAAS platform (e.g. working on a gui, testing developer tools, submitting bug reports, improving documentation, improving an analysis already on the platform).

### Please understand that because this project is heavily integrated with the AWS cloud, we have to vet features and consider the cost any potential changes when accepting contributions.

# Ground Rules

 Responsibilities
 * Ensure compatibility for every change that's accepted for platform deployment.
 * Create issues for any major changes and enhancements that you wish to make. Discuss things transparently and get community feedback.
 * Don't add any classes to the codebase unless absolutely needed. Err on the side of using functions.
 * Keep feature versions as small as possible, preferably one new feature per version.
 * Be welcoming to newcomers and encourage diverse new contributors from all backgrounds. See the [Contributor Covenant](ContributorCovenant.md).

# Your First Contribution
Help people who are new to your project understand where they can be most helpful. This is also a good time to let people know if you follow a label convention for flagging beginner issues.

 If you're unsure where to begin, please consider working through/improving our documentation. You can do so directly in the [source files](docs/build/) or by editing. docstrings.
 Also take a look at our issue tracker where we have flagged good first issues, as well as help wanted issues.


 Working on your first Pull Request? You can learn how from this *free* series, [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github).



# Getting started

For something that is bigger than a one or two line fix:

1. Create your own fork of the code
2. Do the changes in your fork
3. If you like the change and think the project could use it:
    * Be sure you have followed the code style for the project (moving to black style).

 Small contributions such as fixing spelling errors, where the content is small enough to not be considered intellectual property, can be submitted by a contributor as a patch.

As a rule of thumb, changes are obvious fixes if they do not introduce any new functionality or creative thinking. As long as the change does not affect functionality, some likely examples include the following:
* Spelling / grammar fixes
* Typo correction, white space and formatting changes
* Comment clean up
* Bug fixes that change default return values or error codes stored in constants
* Adding logging messages or debugging output
* Changes to ‘metadata’ files like .gitignore, build scripts, etc.
* Moving source files from one directory or package to another

# How to report a bug
If you find a security vulnerability, do NOT open an issue. Email neurocaas[at]gmail.com instead.

In order to determine whether you are dealing with a security issue, ask yourself these two questions:
* Can I access something that's not mine, or something I shouldn't have access to?
* Can I disable something for other people?

If the answer to either of those two questions are "yes", then you're probably dealing with a security issue. Note that even if you answer "no" to both questions, you may still be dealing with a security issue, so if you're unsure, just email us at neurocaas[at]gmail.com.

When filing an issue, make sure to answer these five questions:

1. What version of python are you using?
2. What operating system and processor architecture are you using?
3. What did you do?
4. What did you expect to see?
5. What did you see instead?
6. Are you working with a deployed analysis on neurocaas, or deploying a new one?

# How to suggest a feature

If you find yourself wishing for a feature that doesn't exist in NeuroCAAS, you are probably not alone. Open an issue on our issues list on GitHub which describes the feature you would like to see, why you need it, and how it should work. In the case that you are suggesting a feature for an analysis we already provide, please understand that we may have to discuss with the original implementation authors before committing to a change.

# Code review process

Code is reviewed on a bi-weekly basis by the core team of NeuroCAAS developers. Please expect us to get back to you in that window.

# Code style

We are moving to [black](https://github.com/psf/black) as a shared coding style. Although not necessary, we would appreciate any contributions in that style.

#Labeling conventions

If you discover an issue with a particular analysis implementation, please label the issue with the name of that analysis.

# Attribution
This contribution guideline is based on the contributing template provided at https://github.com/nayafia/contributing-template, and draws heavily from the examples cited there. 
