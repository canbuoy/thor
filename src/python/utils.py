
"""
Functions that are useful in various places, but have no common theme.
"""

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)

import cPickle
import os
import signal
import struct
import sys
import time
import __builtin__

from pprint import pprint
from argparse import ArgumentParser
from multiprocessing import Process, Pipe
from itertools import izip

import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
except:
    logger.warning('could not load matplotlib -- plotting disabled')


class odinparser(ArgumentParser):
    """
    Simple extension of argparse, designed to automatically print stuff
    """
    def parse_args(self):
        print graphic
        args = super(odinparser, self).parse_args()
        pprint(args.__dict__)
        return args
    
        
class ProgressConsoleHandler(logging.StreamHandler):
    """
    A handler class which allows the cursor to stay on one line for selected 
    messages
    
    http://stackoverflow.com/questions/3118059/how-to-write-custom-python-logging-handler?answertab=active#tab-top
    
    Example
    -------
    >>> import time
    >>> progress = ProgressConsoleHandler()
    >>> console  = logging.StreamHandler()  
    
    >>> logger = logging.getLogger('test')
    >>> logger.setLevel(logging.DEBUG) 
    >>> logger.addHandler(progress)
    
    >>> logger.info('test1')
    >>> for i in range(3):
    >>>     logger.info('remaining %d seconds', i, extra={'same_line':True})
    >>>     time.sleep(1)   
    >>> logger.info('test2')
    """
    on_same_line = False
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            same_line = hasattr(record, 'same_line')
            if self.on_same_line and not same_line:
                stream.write(self.terminator)
            stream.write(msg)
            if same_line:
                stream.write('... ')
                self.on_same_line = True
            else:
                stream.write(self.terminator)
                self.on_same_line = False
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def parmap(f, jobs, procs=12):
    """
    Similar to multiprocessing.map(), but can be called from within a class.    
    """
    
    # split the `jobs` into a list of size 
    X = [ jobs[i::procs] for i in range(procs) ]
    
    # now make a function that iterates over all those sub-lists
    def g(list_of_items):
        """ version of `f` that iterates over a list """
        return map(f, list_of_items)
        
    # distribute all the jobs
    def spawn(f):
        """
        Helper function for parmap()
        """
        def fun(pipe,x):
            pipe.send(f(x))
            pipe.close()
        return fun
    
    # send em off to some kiddies
    pipe=[Pipe() for x in X]
    proc=[Process(target=spawn(g),args=(c,x)) for x,(p,c) in izip(X,pipe)]
    
    # wait for kids to finish playing
    [p.start() for p in proc]
    [p.join() for p in proc]
    
    # take toys away from kids
    output = [p.recv() for (p,c) in pipe]
    
    # flatten output
    flat_output = [item for sublist in output for item in sublist]
    
    return flat_output

    
def unique_rows(a):
    """
    For a two-dim array, returns unique rows.
    """
    unique_a = np.unique(a.view([('', a.dtype)]*a.shape[1]))
    return unique_a.view(a.dtype).reshape((unique_a.shape[0], a.shape[1]))
    

def random_pairs(total_elements, num_pairs): #, extra=10):
    """
    Sample `num_pairs` random pairs (i,j) from i,j in [0:total_elements) without
    replacement.
    
    Parameters
    ----------
    total_elements : int
        The total number of elements.
    num_pairs : int
        The number of unique pairs to sample
    
    Returns
    -------
    pairs : np.ndarray, int
        An `num_pairs` x 2 array of the random pairs.
    
    if num_pairs > (total_elements * (total_elements-1)) / 2:
        raise ValueError('Cannot request more than N(N-1)/2 unique pairs')
    
    not_done = True
    
    while not_done:
        n_to_draw = num_pairs + extra
        p = np.random.randint(0, total_elements, size=(num_pairs, 2))
        p.sort(axis=1)
        p = unique_rows(p)
        p = p[ p[:,0] != p[:,1] ] # slice out i == j
        
        if p.shape[0] >= num_pairs:
            p[:num_pairs]
            not_done = False
        else:
            extra += 10
    
    return p[0:num_pairs]
    """

    np.random.seed()
    inter_pairs  = []
    factor = 2
    while len(inter_pairs) < num_pairs:
        rand_pairs   = np.random.randint( 0, total_elements, (num_pairs*factor,2) )
        unique_pairs = list( set( tuple(pair) for pair in rand_pairs ) )
        inter_pairs  = filter( lambda x:x[0] != x[1], unique_pairs)
        factor += 1

    return np.array ( inter_pairs[0:num_pairs] )

def maxima(a):
    """
    Returns the indices where `a` is at a local max.
    """
    return np.where(np.r_[True, a[1:] > a[:-1]] & np.r_[a[:-1] > a[1:], True] == True)[0]
        
    
def write_sample_input(filename='sample.odin'):
    txt=''' # THIS FILE WAS GENERATED BY ODIN -- sample input file
    
    runname: testrun                 # used to name directories, etc.
    
    
    # RUN SETTINGS 
    predict:   boltzmann             # {single, boltzmann, kinetic} ensembles
    sampling:  md                    # either {md, mc} for dynamics, Monte Carlo
    prior:     minimal               # could be amber99sb-ildn, charm22, etc.
    solvent:   none                  # grand cannonical solvent to employ
    outputdir: ~/testrun             # where stuff gets written -- could be GB.
    
    
    # EXPERIMENTS
    experiment: LCLS_run_1           # a name identifying the data
        - dir:  ~/testrun/lcls       # should contain pre-processed data files
        - type: scattering           # {scattering, chemshift} are in now
    
    experiment: NMR_HSQC_1
        - dir:  ~/testrun/chemshifts
        - type: chemshift
        
        
    # RESOURCES
    runmode: cluster                 # one of {local, cluster}
    nodes:   4                       # how many nodes to call for
    gpn:     1                       # gpus per node
    REMD:    True                    # use REMD to estimate the lambdas
    temps:   [1, 0.5, 0.1, 0.01]     # temps in units of beta, <= nodes*gpn
    
    '''
    f = open(filename, 'w')
    f.write(txt)
    f.close()
    logger.info("Wrote: %s" % filename)
    return
    

def plot_polar_intensities(shot, output_file=None):
    """
    Plot an intensity map in polar coordinates.
    
    Parameters
    ----------
    shot : odin.xray.Shot
        A shot to plot.
    output_file : str
        The filename to write. If `None`, will display the image on screen and
        not save.
    """

    pi = shot.polar_grid

    colors = shot.polar_intensities # color by intensity
    ax = plt.subplot(111, polar=True)
    c = plt.scatter(pi[:,1], pi[:,0], c=colors, cmap=cm.hsv)
    c.set_alpha(0.75)

    if output_file:
        plt.savefig(output_file)
        logger.info("Saved: %s" % output_file)
    else:
        plt.show()

    return


graphic = """
	                                    .  
	                                  .#   
	           .                     .##   
	          #.                     #  :  
	       .# .                     .# .#  
	       .. .       ..##.         #   #  
	       #  .     .#.    #       #    #  
	             .#         #.    #    #   
	      #    #             #.  #.    #   
	      # .#                ##      #    
	      ##.                #.      :#       ____  _____ _____ _   _ 
	      #                 .# .:   .#       / __ \|  __ \_   _| \ | |
	   .:.      .    .      .#..   .#       | |  | | |  | || | |  \| |
	  .####  . . ...####     #.   #.        | |  | | |  | || | | . ` |
	 # .##   . # . #.#   . =# .##.#         | |__| | |__| || |_| |\  |
	 . .##   .  #   ..   # = .=#  #          \____/|_____/_____|_| \_|
	#   . ####     .###,  ,      ##        
	#.## .               '#.. #    #                       Observation
	 .                      ##.. . #       	               Driven
	                          .#   #                       Inference
	                            #. /                   of eNsembles
		                        .#        

     ----------------------------------------------------------------------
"""
