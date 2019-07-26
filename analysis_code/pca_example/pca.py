## Toy code that runs pca on numpy arrays that are given as input, visualizes the projection to first n pcs.  

import sys
import datetime
import joblib
import numpy 
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA


def reduce_data(data):
    '''
    Reduce the dimensionality of the data to the top two pcs. 
    '''
    n_components = 2
    pca = PCA(n_components = n_components)
    ## fit the data: 
    projected = pca.fit_transform(data)
    return projected

def plot_data(projected):
    '''
    Plot the dimensionality reduced data, and save the resulting figure. 
    '''
    fig,ax = plt.subplots()
    ax.set_title('Projection Visualization')
    ax.set_xlabel('PC 1')
    ax.set_ylabel('PC 2')
    ax.scatter(projected[:,0],projected[:,1])
    plt.savefig('Example_fig'+str(datetime.datetime.now())+'.png')

def main(filename):
    data = joblib.load(filename)
    projected = reduce_data(data)
    plot_data(projected)

if __name__ == '__main__':
    filename = sys.argv[1]
    main(filename)




    



