# -------------------------------------------------
# --------------------- graphwidget.py ------------
# -------------------------------------------------
from  PyQt5.QtWidgets  import *
from  matplotlib.backends.backend_qt5agg  import  FigureCanvas
from  matplotlib.figure  import  Figure
import numpy as np
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    
class  graphWidget(QWidget):
    """
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas  = FigureCanvas(Figure())
        self.layout().addWidget(NavigationToolbar(self.canvas, self))
        self.layout().addWidget(self.canvas)
    """
    def  __init__(self, parent = None):

        QWidget.__init__(self,  parent)
        
        self.canvas  =  FigureCanvas(Figure())
        
        vertical_layout  =  QVBoxLayout () 
        vertical_layout.addWidget ( self.canvas )
        
        self.canvas_axes  =  self.canvas.figure.add_subplot( 111 ) 
        self.setLayout( vertical_layout )
        
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(NavigationToolbar(self.canvas, self))
        
        
        #Matplotlib Script
        #t = np.arange(0.0, 2.0, 0.01)
        #s = 1 + np.sin(2 * np.pi * t)
        #self.canvas_axes.plot(t, s)
        self.canvas_axes.set(xlabel='time (s)', ylabel='voltage (mV)', title='This is the title')
        self.canvas_axes.grid()

    def plotData(self, xs, ys):
        self.canvas_axes.plot(xs, ys)
        #self.canvas_axes.set(xlabel='time (s)', ylabel='voltage (mV)', title='About as simple as it gets, folks')
        #self.canvas_axes.grid()