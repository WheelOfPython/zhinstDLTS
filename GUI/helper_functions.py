import os
import matplotlib.pyplot as plt

def plotGraph(xs, ys):
    #plt.plot(xs * 10**3, ys * 10**12) #NumPy lists...
    plt.plot(xs, ys)
    plt.xlabel("Time(ms)")
    plt.ylabel("Capacitance(pF)")
    plt.title("Transient Capacitance")
    plt.show()

def createFile(name, ext='.txt'):
    if os.path.isfile(name + ext):
        data_file = open('R' + name + ext, 'w')
    else:
        data_file = open(name + ext, 'w')
    return data_file