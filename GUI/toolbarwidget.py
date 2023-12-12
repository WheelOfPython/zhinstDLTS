# -------------------------------------------------
# --------------------- toolbarwidget.py ------------
# -------------------------------------------------
from  PyQt5.QtWidgets  import *
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    
class  toolbarWidget(QToolBar):
    
    def  __init__(self, parent = None):

        QToolBar.__init__(self,  parent)
        
    #def rend(self, gui):
    #    self.addToolBar(NavigationToolbar(gui.graphWidget.canvas, self))