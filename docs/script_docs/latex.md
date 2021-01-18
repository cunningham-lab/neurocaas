
Script documentation for file: latex, Updated on:2020-12-30 18:30:29.631091
===========================================================================

# Latex Github workflow.


Set up our overleaf project with github. It now exists as an independent repository. Although it currently also exists as a submodule of the neurocaas repository, this submodule is not updating as expected [this](https://stackoverflow.com/questions/40987847/unable-to-find-current-origin-master-revision-in-submodule-path)does not work for me. This is fine however, as the integration with the neurocaas repository is not necessary for productively working on text revisions. I also took the following steps:
- downloaded maclatex for analogous package support to overleaf.
- created a file `revision.tex` that is based off of the main file.
- created a file `results_main.tex` that summarizes the main results separately and can be included as input to the main file.
- figured out issues with bibliography:
    -  1. had to download humannat.bst file to the repository
    -  2. had to run `xelatex [filename.tex]` to generate auxfile`
    3. had to run `bibtex [filename (noextension)]` to generate a .bbl file
    4. had to run `xelatex [filename.tex]` *multiple times* in order to get the citations to show up.


It looks like running latex multiple times is a known part of working with latex locally- this is confusing and seems wrong to me, but is good for intuition.