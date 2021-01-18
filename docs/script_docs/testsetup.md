
Script documentation for file: testsetup, Updated on:2020-12-12 17:11:38.727646
===============================================================================

# Testing your scientific python code (with Docker and AWS)


Writing tests is still a fairly rare practice in scientific data analysis software. However, I have found that writing tests is incredibly useful, and increases the productivity of work overall. Furthermore, I found that the usefulness of writing tests scales directly with the size and complexity of the project that you are working on. As scientific software projects integrate other layers of the computational environment as part of their distribution (i.e. containerization through docker and hardware at scale through AWS), tests become even more important than before. Although it might seem difficult to integrate these technologies into testing frameworks, I will discuss some important frameworks that lower the barrier to writing efficient tests in the context of these technologies. The following insights are not new by any means, but they were crucial points in my decision to reorganize my code around tests.
## Why write tests?


I've often heard from other computational researchers that it's not worthwhile to organize one's code because we most often end up using it once, and then throwing it away once the relevant publication is out. While this may be true in certain cases, here are a few points against that argument:

*Reproducibility matters.* To start off, here's a standard argument from the scientific ethics viewpoint: disorganized code is often brittle and fragile code that can break when run in any context too far away from the one in which it was originally written. This could mean somebody else's machine when they are trying to reproduce your results with your code, or your own machine a few months later when you need to change the colors on a figure. Experience and literature (see Stodden science paper) says that code that is written with the intention of being used once can most often only be used once. Beyond the broad ethical implications of unreproducible results due to code, it's can be extremely demoralizing to come back to something that you thought worked and have it break on you, even in a pretty minor way. This point counts double if you've just spent an entire paper trying to convince other people that it works.

*You're slowing yourself down if you don't* In my personal experience, I've never had a project where I never had to reorganize my code. This could be something simple as changing a variable name, factoring out some part of your script into a function, or reorganizing the way that you accept input whole hog. In any of these cases, reorganizing my code without tests always introduces a certain amount of uncertainty that my code is still doing what I thought it did. Does that figure that I generated still look the same after I re-implemented PCA? If not, is that because of a random seed, or an error that I caught, or an error that I introduced? After a while, these multiplying uncertainties can undermine your ability to reorganize your code when you need it, or sap your motivation to try out new and different things for fear of breaking what you already have. These effects can drastically slow down the rate at which I make progress in my projects.

*Testing distinguishes science and engineering* One big insight that I had when I started writing scientific tests is that it's fundamentally wrong that the first data your code sees is the data that you're trying to analyze. When we are trying to write data analysis software, there are two kinds of uncertainty:1) does my analysis software do what I think it does? and 2) what happens when I apply my analysis software to scientific data? As data scientists, we _must_ be able to distinguish this first type of uncertainty (an engineering problem) from the second (a scientific problem). If data analysis software only ever sees the data it was designed to analyze, it's nearly impossible to distinguish between these issues, especially if you take the previous two points seriously. You have to have test data (fixtures?) where you understand the expected output of your analysis software, and you should be applying your software to this test data any time you make a change to it. Fundamentally, writing tests for your data analysis code means committing to the fact that most of your time and energy as a scientist is devoted to building functional scientific infrastructure, and that actually seeing cool results is the reward for this hard work

*Writing tests enforces other good work habits* As data scientists, we are fundamentally embedded in an open source community of software developers. This community is many times larger than the computational science community will ever be, and there are many tools and lessons that we can adopt from this community. Before I started to write explicit, separate test suites, I had a variety of different code development workflows: having all my code in a jupyter notebook and checking everything there, importing modules into a jupyter notebook that ran interactively and running tests on my data, importing and checking software from the IPython console, etc. All of these different workflows have major issues that prevented me from writing and testing code in an effective way. Although there were tools that could help with this issue (like the %debug or %aimport magics), I found that they always had unintended consequences or did not cover all of the use cases that came up in my work. For example, how do you avoid restarting the interpreter you're testing your custom analysis module in IPython and discover a bug? Autoimports are nice, but they will still cause issues if you're writing object-oriented code (new attributes and methods don't always work correctly). These issues push developers towards having more of their code be editable in their interactive environment, discouraging practices like structuring source code in a python package. On the other hand, once you start writing tests, you start to see the value and power in a deluge of open source development tools, like branch and pull-request workflows on Github, Continuous Integration, Coverage Reports, and the functionality of Python Packages (command line tools, dependency and environment management etc.). Finally, and perhaps more importantly, it formats your work in the common, agreed upon language of open source software development, meaning that your project can now be better understood, critiqued, and improved by the whole community. Being able to collaborate with others and learn from them will exponentially increase the speed at which you can work.
## What does a test look like?

- Separate module, import from src
- Pytest based exposition
- Test data (keep things small)
- Structure your code so that its easy to test (the arguments are easy to simulate, the outputs are easy to check)
- Make fixtures for initialization of tests
- Consider all test cases
- If you can't easily create fake data, consider monkeypatching

## How do tests work with docker and aws?

- L
- o
- c
- a
- l
- s
- t
- a
- c
- k
-  
- i
- s
-  
- m
- a
- g
- i
- c
