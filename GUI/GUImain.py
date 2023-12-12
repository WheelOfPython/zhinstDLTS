import sys
from PyQt5.QtWidgets import *
from PyQt5 import uic, QtCore, QtWidgets
import numpy as np
import matplotlib.pyplot as plt
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QApplication, QWidget
from  matplotlib.figure  import  Figure
###########################################
import matplotlib.pyplot as plt
from helper_functions import *
from datetime import datetime
#import zhinst.ziPython as zi
import numpy as np
import math
import time
import os

###
def connectDevice(Id):
    discovery= zi.ziDiscovery()
    device_id = discovery.find(Id)
    device_props = discovery.get(device_id)
    daq = zi.ziDAQServer(device_props['serveraddress'], device_props['serverport'], device_props['apilevel'])
    return daq

def setSettings(daq, variables):
    ##___daq.factory_reset()___
    # Settings
    daq.setInt('/dev5298/imps/0/mode', 1) # 2-terminal
    daq.setInt('/dev5298/imps/0/auto/output', 0) # test singal ampl to manual
    daq.setDouble('/dev5298/imps/0/output/amplitude', variables['voltage_ampl'])
    daq.setDouble('/dev5298/imps/0/freq', variables['oscilation_freq'])
    # Advanced Settings
    daq.setInt('/dev5298/system/impedance/filter', 1)  # Enable advanced settings??
    daq.setInt('/dev5298/system/impedance/calib/cablelength', 1)
    daq.setDouble('/dev5298/imps/0/maxbandwidth', 100000)
    daq.setDouble('/dev5298/imps/0/demod/rate', 107000) # Sa/s data trasfer rate
    daq.setDouble('/dev5298/imps/0/output/range', 10) # AUX range
    # Threshold
    daq.setInt('/dev5298/tu/thresholds/0/input', 59)
    daq.setDouble('/dev5298/tu/thresholds/0/activationtime', variables['pulse_high_state'])
    daq.setDouble('/dev5298/tu/thresholds/0/deactivationtime', variables['pulse_low_state'])
    daq.setInt('/dev5298/tu/logicunits/0/inputs/0/not', 1)
    # AUX --> Aux output = (signal+preoffset)*scale + offest
    daq.setInt('/dev5298/auxouts/0/outputselect', 13)
    daq.setDouble('/dev5298/auxouts/0/scale', variables['pulse_height'])
    daq.setDouble('/dev5298/auxouts/0/offset', variables['pulse_offset'])
    # Lock-in
    daq.setInt('/dev5298/sigouts/0/add', 1)


def setDAQsettings(daq_module, variables):
    daq_module.set('device', variables['DeviceID'])
    # Set software Trigger
    daq_module.set('triggernode', '/dev5298/imps/0/sample.Param1') # use capacitance as SW trigger
    daq_module.set('findlevel', 1)                                 # automatically find the trigger level
    # Settings
    daq_module.set('grid/mode', 2)         # 1: nearest, 2: linear, 3: excact
    daq_module.set('grid/cols', variables['points'])      # this sets the capture duration, which is 500/13k~38ms #The duration by default equals to 500Sa/13kSa/s=38ms
    daq_module.set('duration', variables['total_duration'])      # total duration of capture
    daq_module.set('grid/repetitions', 1)  # average sampling over N repetitions
    daq_module.set('edge', 2)              # 0:none, 1:positive, 2:negative, 3:both
    daq_module.set('holdoff/time', 0.200)   # must be >> than duration(otherwise overlaping frames) rearming of tirgger
    #delay = variables['pulse_high_state'] varibles['total_duration']
    daq_module.set('delay', variables['delay'])         # delay until daq


def gatherData(daq, variables, subs):
    daq.unsubscribe('*')  # Unsubscribe from any streaming data
    daq.sync()            # Flush all the buffers.

    # Preparations
    daq_module = daq.dataAcquisitionModule()
    setDAQsettings(daq_module, variables)
    for sub in subs:
        daq_module.subscribe(sub)

    # Run DAQ
    daq_module.execute()
    timeout = 100
    start = time.time()
    while not daq_module.finished():
        time.sleep(0.2)
        progress = daq_module.progress()    # Progress indicator
        print("Individual DAQ progress: {:.2%}.".format(progress[0]), end="\r")
        if (time.time() - start) > timeout: # Error handling
            print("\nDAQ still not finished, focring finish...")
            daq_module.finish()
    print("Individual DAQ progress: {:.2%}.".format(progress[0]))

    rdata = daq_module.read(True)
    clk = float(daq.getInt("/dev5298/clockbase"))
    daq_module.unsubscribe('*')
    daq_module.clear()  # ???
    
    return (clk, rdata)


# data -> {'info': [name, units], 'values': [[col1], [col2], ...]
def refineData(rdata):
    clk = rdata[0]
    data = rdata[1]
    Outputs = {
        'P0': data["/dev5298/imps/0/sample.param0.avg"],
        'P1': data["/dev5298/imps/0/sample.param1.avg"],
        'ReZ': data["/dev5298/imps/0/sample.realz.avg"],
        'ImZ': data["/dev5298/imps/0/sample.imagz.avg"]
    }

    ts = Outputs['P1'][0]['timestamp'][0]
    zs = Outputs['P1'][0]['value'][0]

    data['info'] = {
        'Name': datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
        'Units': '         ms               F',
        'Size': len(zs),
        'Clock': clk
    }

    data['values'] = [ts, zs]
    return data

# data -> {'info': [name, units], 'values': [[col1], [col2], ...]
def saveData(data, sep=','): # tab -> '\t'
    data_file = createFile(data['info']['Name'])  # Name
    data_file.write(data['info']['Units']+'\n')   # Units
    for i in range(data['info']['Size']):
         t_point = (data['values'][0][i] - data['values'][0][0]) / data['info']['Clock'] * 1000 #raw_time -> ms
         z_point = data['values'][1][i] #* 10**12 # F -> pF
         data_file.write("{: .4E}{}{: .4E}\n".format(t_point, sep, z_point))
    data_file.close()

def MainLoop(gui, variables, subs):
    #------------ Connection ----------------
    daq = connectDevice(variables['DeviceID'])
    logText = "<font color=\"" + 'red' + "\">" + "connected device!" + "</font>"
    gui.plain.appendHtml(logText)
    #------------ Initialization ------------
    setSettings(daq, variables)
    logText = "<font color=\"" + 'red' + "\">" + "setting variables!" + "</font>"
    gui.plain.appendHtml(logText)
    #------------ Data Gathering ------------
    logText = "<font color=\"" + 'red' + "\">" + "aquiring data!" + "</font>"
    gui.plain.appendHtml(logText)
    raw_data = gatherData(daq, variables, subs)
    data     = refineData(raw_data)
    # ------------ Saving Data ---------------
    logText = "<font color=\"" + 'red' + "\">" + "saving data!" + "</font>"
    gui.plain.appendHtml(logText)
    saveData(data, sep='\t')
    # ------------ Plotting Data -------------
    logText = "<font color=\"" + 'red' + "\">" + "ploting data!" + "</font>"
    gui.plain.appendHtml(logText)
    t_point = []
    z_point = []
    for i in range(0, data['info']['Size']):
        t_point.append((data['values'][0][i] - data['values'][0][0]) / data['info']['Clock'] * 1000)  # raw_time -> ms
        z_point.append(data['values'][1][i] * 10 ** 12)  # F -> pF
    #plotGraph(t_point, z_point)  # <---???
    gui.graphWidget.plotData(t_point, z_point)
    gui.graphWidget.canvas.draw()

###

#==================================================================================


class MyGUI(QMainWindow):
    def __init__(self):
        super(MyGUI, self).__init__()
        uic.loadUi("mygui.ui", self)
        self.show()
        self.setWindowTitle("PyQt5 & Matplotlib Example GUI")
        #self.actionclose.triggered.connect(lambda: self.close())
    #-------------------------------------------------------
    
        self.button_points.clicked.connect(self.set_points)
        self.button_scale.clicked.connect(self.set_scale)
        self.button_dely.clicked.connect(self.set_dely)
        self.button_high.clicked.connect(self.set_high)
        self.button_low.clicked.connect(self.set_low)
        self.button_offset.clicked.connect(self.set_offset)
        self.button_dur.clicked.connect(self.set_dur)
        self.button_oscfreq.clicked.connect(self.set_oscfreq)
        self.button_vampl.clicked.connect(self.set_vampl)
        
        
        self.button_start.clicked.connect(self.runit)
        
        #self.toolbarWidget.rend(self)
        #self.addToolBar(QtCore.Qt.RightToolBarArea, NavigationToolbar(self.graphWidget.canvas, self))
        self.graphWidget.canvas.draw()
        
        self.vampl = 0.300
        self.oscfreq = 100000
        self.scale = 3      
        self.offset = 0     
        self.high = 0.010  
        self.low = 0.050
        self.dur = 0.005  
        self.dely = -0.002
        self.points = 2048
        
        
        
    
    #---------------- BUTTONS ------------------
    """ 
    def set_points(self):
        val = float(self.edit_points.text())
        if val.type == "Float":
            self.points = val
            logText = "<font color=\"" + 'red' + "\">" + self.points + "</font>"
            self.plain.appendHtml(logText)
    """

    def set_points(self):
        try:
            val = float(self.edit_points.text())
            self.points = val
            logText = "<font color=\"" + 'red' + "\">" + str(self.points) + "</font>"
            self.plain.appendHtml(logText)
        except ValueError:
            print("Not a Float")


    def set_scale(self):
        logText = "<font color=\"" + 'orange' + "\">" + self.edit_scale.text() + "</font>"
        self.plain.appendHtml(logText)
        
        t = np.arange(0.0, 2.0, 0.01)
        s = 1 + np.sin(2 * np.pi * t)
        
        self.graphWidget.plotData(t, s)
        self.graphWidget.canvas.draw()
    
    def set_offset(self):
        self.offset = float(self.edit_offset.text())
    def set_dely(self):
        self.dely = float(self.edit_dely.text())
    def set_high(self):
        self.high = float(self.edit_high.text())
    def set_low(self):
        self.low = float(self.edit_low.text())
    def set_dur(self):
        self.dur = float(self.edit_dur.text())
    def set_vampl(self):
        self.vampl = float(self.edit_vampl.text())
    def set_oscfreq(self):
        self.oscfreq = float(self.edit_oscfreq.text())
    
    
    #----------------- OTHER ----------------------
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Quit?',
                                     'Are you sure you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if not type(event) == bool:
                event.accept()
            else:
                sys.exit()
        else:
            if not type(event) == bool:
                event.ignore()
    
    def runit(self):
        self.variables = {
        'DeviceID'           : 'dev5298',
        'voltage_ampl'       : self.vampl, #0.300 ,  #V
        'oscilation_freq'    : self.oscfreq, #100000,  #Hz
        'pulse_height'       : self.scale, #3     ,  #V
        'pulse_offset'       : self.offset, #0     ,  #V
        'pulse_high_state'   : self.high, #0.010 ,  #s
        'pulse_low_state'    : self.low, #0.050 ,  #s
        'total_duration'     : self.dur, #0.005 ,  #s 0.039155 -> 39.155 ms (same as katagrafi duaration?)
        'delay'  : self.dely,   #-0.002,
        'points' :  self.points #2048
        }
        self.subs = ['/dev5298/imps/0/sample.Param1.avg',
            '/dev5298/imps/0/sample.RealZ.avg' ,
            '/dev5298/imps/0/sample.ImagZ.avg' ,
            '/dev5298/imps/0/sample.Param0.avg']
        print(self.variables)
        #MainLoop(self, self.variables, self.subs)



def main():
    app = QApplication(sys.argv)
    window = MyGUI()
    app.exec()

if __name__ == '__main__':
    main()
