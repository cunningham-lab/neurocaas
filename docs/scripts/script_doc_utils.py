## Module to help incorporate active documentation into your work framework. Initialize documents, embed images, create tables, etc. 
import pathlib
import __main__
import os
from collections import OrderedDict
import datetime
import matplotlib.pyplot as plt
from mdutils.mdutils import MdUtils
from mdutils import Html

pathname = "../script_docs/"

def initialize_doc(linkdict = None):
    """Initializes a markdown document in docs/script_docs named after this script with a correctly updated date. 

    :param linkdict: A dictionary with keys in [prev,next,parent]. The corresponding values are the names of the files that we should link to, which are assumed to exist in the script docs directory. Do not provide the .md extension. 
    :returns: a mdutils mdfile object. Must be written (invoke `mdfile.create_md_file`) in order to manifest a real file. 
    """
    filename = pathlib.Path(__main__.__file__).stem 
    mdFile = MdUtils(file_name = os.path.join(pathname,filename),title = "Script documentation for file: "+ filename+", Updated on:" +str(datetime.datetime.now()))
    if linkdict is not None:
        mdFile.write(" \n")
        linklocs = OrderedDict([("parent","left"),("prev","left"),("next","left")])
        for l in linklocs.keys():
            if l not in linkdict.keys():
                print("File has no {}, skipping".format(l))
                continue
            else:
                filename = linkdict[l] 
            assert os.path.exists(os.path.join(pathname,filename+".md")), ("The file {}.md does not exist in the script_docs folder.".format(filename))
            file_text = "{} file: ".format(l)+mdFile.new_inline_link(text = filename,link = "./{}.md".format(filename))
            mdFile.new_line(file_text,align = linklocs[l],bold_italics_code = 'b')



    return mdFile


def insert_image(md,path,size = None,align = None):
    """Inserts an image at a new line in the markdown document. Can do basic image formatting as well: size can be specified as a list [width, height], and/or aligned. 

    :param md: mdfile object. 
    :param path: the path to an image file. 
    :param size: a list specifying the width and height of the new array. One entry can be none to just change one aspect of the image. 
    :param align: provides alignment according to Html.image specifications. i.e. 'center'
    """
    ## parse arguments:
    if size:
        assert type(size) is list, "size must be a list"
        assert len(size) == 2, "size must have two elements (width and height)"
        assert not all([s is None for s in size]), "one entry must be non-none"
        if size[0] is None:
            size = "x{}".format(size[1])
        elif size[1] is None:
            size = str(size[0])
        else:
            size = "{w}x{h}".format(w=size[0],h=size[1])
    if align:
        assert type(align) is str, "align argument must be string."

    assert path.startswith("./images/"),"path must assume we are in the script_docs directory. "

    md.new_line(Html.image(path=path, size=size, align=align))

def get_relative_image_path(path):
    """Given a path to an image that is stored somewhere in the script_docs directory, returns the relative path that insert_image should reference to that image.  

    :param path: string path to image. Should contain script_docs at some point. 
    """

    rel_path = "./{}".format(path.split("script_docs/")[-1])
    assert rel_path is not None, "media must be in the script_docs directory or a subdirectory thereof. "
    return rel_path

def save_and_insert_image(md,fig,path,size = None,align = None):
    """Saves a matplotlib figure as an image, and then inserts that image into the provided markdown document. Note: will close the figure, so make sure you are done with it.  

    :param md: mdfile object. 
    :param fig: matplotlib figure object.
    :param path: the path to an image file. 
    :param size: a list specifying the width and height of the new array. One entry can be none to just change one aspect of the image. 
    :param align: provides alignment according to Html.image specifications. i.e. 'center'
    """
    fig.savefig(path)
    plt.close(fig)
    insert_image(md,get_relative_image_path(path),size,align)
    return get_relative_image_path(path)

def insert_vectors_as_table(md,vectors,labels):
    """Adds the values of vectors to a markdown document as a table. 

    :param md: mdfile object.
    :param vectors: a numpy array containing column vectors that will be inserted into a table 
    :param labels: a list of the labels for each of the given column vectors.
    """
    length,nb = vectors.shape
    assert len(labels) == nb,"the number of labels must match the number of column vectors given."
    veclist = labels
    flatlist = vectors.flatten().astype(str).tolist()
    veclist.extend(flatlist)
    md.new_line("  \n")
    md.new_table(columns = nb,rows = length+1,text = veclist,text_align = "center")
