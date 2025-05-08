
# import required modules
import numpy as np
from scipy import signal
import math
import os
from classDef import *

def filterGRF(settings):
    external_loads = settings.external_loads_file
    base = external_loads.replace(os.path.abspath(settings.mocap_dir+'/'),"").replace('_ext_loads.xml',"")
    grf = os.path.abspath(settings.mocap_dir+'/') + base + '-original.mot'
    grf_filtered = settings.mocap_dir + '/' + base + '.mot'
    f  = open(grf, 'r')
    f2 = open(grf, 'r')
    f3 = open(grf, 'r')
    n = open(grf_filtered, 'w')
    numLine = len(f3.readlines())
    numCol = 19
    order = 4
    cutoff = 40 # Hz
    b, a = signal.butter(order, cutoff, 'lp',fs=241) #Sampling frequency may change
    y = np.empty(shape=(numLine-6, numCol))
    x = np.empty(shape=(numLine-6, numCol))

    count = 0
    for line in f:
        lineVal = line.split("\t")
        if count > 5:
            x[count-6,:] = np.array(lineVal[:len(lineVal)-1])
        count = count + 1

    for i in range (0,numCol):
        if i > 0 and i < numCol - 6:
            y[:,i] = signal.filtfilt(b, a, x[:,i], padtype = None)
        elif i > 0 and i >= numCol - 6:
            y[:,i] = 0.000
        else:
            y[:,i] = x[:,i]

    count = 0
    sep = "\t"
    for line in f2:
        lineVal = line.split("\t")
        if count > 5:
            nLine = sep.join([sep.join(map(str,y[count-6,:].tolist())),"\n"])
        else:
            nLine = sep.join(lineVal)
        n.writelines(nLine)
        count += 1

    # Closing files
    f.close()
    f2.close()
    n.close()



