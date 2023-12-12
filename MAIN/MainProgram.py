import matplotlib.pyplot as plt
from helper_functions import *
from datetime import datetime
import zhinst.ziPython as zi
import numpy as np
import math
import time
import os

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

def MainLoop(variables, subs):
    #------------ Connection ----------------
    daq = connectDevice(variables['DeviceID'])
    #------------ Initialization ------------
    setSettings(daq, variables)
    #------------ Data Gathering ------------
    raw_data = gatherData(daq, variables, subs)
    data     = refineData(raw_data)
    # ------------ Saving Data ---------------
    saveData(data, sep='\t')
    # ------------ Plotting Data -------------
    t_point = []
    z_point = []
    for i in range(0, data['info']['Size']):
        t_point.append((data['values'][0][i] - data['values'][0][0]) / data['info']['Clock'] * 1000)  # raw_time -> ms
        z_point.append(data['values'][1][i] * 10 ** 12)  # F -> pF
    plotGraph(t_point, z_point)  # <---???

###############################################################################
#                              --- MAIN LOOP ---                              #
###############################################################################

if __name__ == '__main__':
    #------------ Set Envirement ------------
    os.chdir("C:\\Users\\Lab Laptop\\Desktop\\FINAL\\DAQ_SAVES")

    #------------ User Input ----------------
    variables = {
    'DeviceID'           : 'dev5298',
    'voltage_ampl'       : 0.300 ,  #V
    'oscilation_freq'    : 100000,  #Hz
    'pulse_height'       : 3     ,  #V
    'pulse_offset'       : 0     ,  #V
    'pulse_high_state'   : 0.010 ,  #s
    'pulse_low_state'    : 0.050 ,  #s
    'total_duration'     : 0.005 ,  #s 0.039155 -> 39.155 ms (same as katagrafi duaration?)
    'delay'  : -0.002,
    'points' :  2048
    }
    subs = ['/dev5298/imps/0/sample.Param1.avg',
            '/dev5298/imps/0/sample.RealZ.avg' ,
            '/dev5298/imps/0/sample.ImagZ.avg' ,
            '/dev5298/imps/0/sample.Param0.avg']

    #------------ RUN ----------------
    MainLoop(variables, subs)