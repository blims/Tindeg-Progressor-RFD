

#!/usr/bin/env python3


import platform
import logging
import asyncio
import struct
import csv
import datetime



from bleak import BleakClient
from bleak import discover
from bleak import _logger as logger
import threading


import os
import pandas as pd
from tkinter import *
import tkinter.messagebox
import tkinter as tk
import time
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
matplotlib.use('TkAgg')






TARGET_NAME = "Progressor"

CMD_TARE_SCALE = 100
CMD_START_WEIGHT_MEAS = 101
CMD_STOP_WEIGHT_MEAS = 102
CMD_START_PEAK_RFD_MEAS = 103
CMD_START_PEAK_RFD_MEAS_SERIES = 104
CMD_ADD_CALIBRATION_POINT = 105
CMD_SAVE_CALIBRATION = 106
CMD_GET_APP_VERSION = 107
CMD_GET_ERROR_INFORMATION = 108
CMD_CLR_ERROR_INFORMATION = 109
CMD_ENTER_SLEEP = 110

RES_CMD_RESPONSE = 0
RES_WEIGHT_MEAS = 1
RES_RFD_PEAK = 2
RES_RFD_PEAK_SERIES = 3
RES_LOW_PWR_WARNING = 4

progressor_uuids = {
    "7e4e1701-1ea6-40c9-9dcc-13d34ffead57": "Progressor Service",
    "7e4e1702-1ea6-40c9-9dcc-13d34ffead57": "Data",
    "7e4e1703-1ea6-40c9-9dcc-13d34ffead57": "Control point",
}

progressor_uuids = {v: k for k, v in progressor_uuids.items()}

PROGRESSOR_SERVICE_UUID = "{}".format(
    progressor_uuids.get("Progressor Service")
)
DATA_CHAR_UUID = "{}".format(
    progressor_uuids.get("Data")
)
CTRL_POINT_CHAR_UUID = "{}".format(
    progressor_uuids.get("Control point")
)

csv_filename = None
csv_tags = {"weight" : None,
            "time" : None}
start_time = None
status_text = "Wake up the Progressor and press Connect"


recording = False
tare = False


def generateFileName():
    global fileName
    ts = time.time()
    fileName = "measurements_" + \
    datetime.datetime.fromtimestamp(
            ts).strftime('%Y-%m-%d_%H-%M-%S')+'.csv'
    print(fileName)

def csv_create():

    global csv_filename
    csv_filename = 'data.tmp'

    try:
        f = open(csv_filename, "w+")
        f.close()
    except:
        print('tmp file was not found')

    with open(csv_filename, 'a', newline='') as csvfile:
        logwrite = csv.DictWriter(csvfile, csv_tags.keys())
        logwrite.writeheader()



def csv_write(value, useconds):
    global csv_filename
    global start_time

    csv_tags['weight'] = "{0:.3f}".format(value)
    csv_tags['time'] = useconds
    print(csv_tags)
    try:
        with open(csv_filename, 'a', newline='') as csvfile:
            logwrite = csv.DictWriter(csvfile, csv_tags.keys())
            logwrite.writerow(csv_tags)
    except Exception as e:
        print(e)




def notification_handler(sender, data):
    global status_text
    """ Function for handling data from the Progressor """
    try:
        if data[0] == RES_WEIGHT_MEAS:
            print("Payload size : {0}".format(data[1]))

            value = [data[i:i+4] for i in range (2, len(data), 8)]
            timestamp = [data[i:i+4] for i in range (6, len(data), 8)]
            # Log measurements to csv file
            for x, y in zip(value,timestamp):
                weight, = struct.unpack('<f', x)
                useconds, = struct.unpack('<I', y)
                csv_write(weight, useconds)
        elif data[0] == RES_LOW_PWR_WARNING:
            print("Received low battery warning.")
            status_text = 'Received low battery warning'
    except Exception as e:
        print(e)




async def run(loop, debug=False):
    global status_text
    if debug:
        import sys

        # loop.set_debug(True)
        #l = logging.getLogger("bleak")
        # l.setLevel(logging.DEBUG)
        #h = logging.StreamHandler(sys.stdout)
        # h.setLevel(logging.DEBUG)
        # l.addHandler(h)

    devices = await discover()
    for d in devices:
        if d.name[:len(TARGET_NAME)] == TARGET_NAME:
            address = d.address
            print("Found \"{0}\" with address {1}".format(d.name, d.address))
            status_text = "Found \"{0}\" with address {1}".format(d.name, d.address)
            break



    try:
        async with BleakClient(address, loop=loop) as client:
            global tare
            global connected
            global duration
            global recording


            x = await client.is_connected()
            print("Connected: {0}".format(x))
            status_text = "Connected to {0}".format(d.name)
            connected = True
            await client.start_notify(DATA_CHAR_UUID, notification_handler)
            await asyncio.sleep(2, loop=loop)

            while connected:


                if recording == True:
                    status_text = 'Recording data...'
                    await client.write_gatt_char(CTRL_POINT_CHAR_UUID, bytes([CMD_START_WEIGHT_MEAS]),response=True)
                    await asyncio.sleep(duration, loop=loop)
                    await client.write_gatt_char(CTRL_POINT_CHAR_UUID, [CMD_STOP_WEIGHT_MEAS])
                    status_text = 'Recording finished'
                    recording = False

                if tare == True:
                    status_text = 'Taring...'
                    await client.write_gatt_char(CTRL_POINT_CHAR_UUID, bytes([CMD_TARE_SCALE]),response=True)
                    await asyncio.sleep(2, loop=loop)
                    status_text = 'Device has been tared'
                    tare = False


                await asyncio.sleep(0.1, loop=loop)

            await client.write_gatt_char(CTRL_POINT_CHAR_UUID, [CMD_ENTER_SLEEP])
            await asyncio.sleep(1, loop=loop)
            status_text = 'Progressor has been disconnected'
    except:
        print('Unable to establish connection')
        status_text = 'Unable to establish connection'



def _asyncio_thread(async_loop):
    async_loop.run_until_complete(run(async_loop, debug=False))


def do_tasks(async_loop):

    threading.Thread(target=_asyncio_thread, args=(async_loop,)).start()












def main(async_loop):


    def connect():
        global status_text
        status_text = 'Scanning for a Progressor...'
        do_tasks(async_loop)


    def start():
        global recording
        global duration
        duration = int(durationEntry.get())
        csv_create()
        generateFileName()
        recording = True


    def tare():
        global tare
        tareAnswer = tkinter.messagebox.askokcancel(title='Tare', message='Keep your hands off the grip and press OK to tare the Progressor.')
        if tareAnswer == True:
            tare = True


    def disconnect():
        global connected
        connected = False


    def csv_save():
        global fileName
        global status_text
        try:
            data = pd.read_csv('data.tmp')

            #export_file_path = filedialog.asksaveasfile(defaultextension='.csv')
            #df.to_csv (export_file_path, index = False, header=True)


            #data.to_csv(r fileName)
            status_text = 'Data saved as ' + fileName
        except:
            status_text = 'Nothing to save'

    def status_bar_refresh():
        global status_text
        status_bar.config(text=status_text)





#######################################################################################################################
# RFD
#######################################################################################################################
    def rfdCalc():

        rfdData = pd.read_csv('data.tmp')

        onset = float(thresholdEntry.get())


        def v_interpolated(rfd_time, title, sub_plot_number):
            # calculates the intersection point between a vertical line and the load curve

            index_p1 = abs(rfdData['offset_time'] - rfd_time).idxmin()
            # make sure the index is of the point below the value
            if (rfdData.iloc[index_p1]['offset_time'] >= rfd_time):
              index_p1 = index_p1 -1

            # The points of the line segment that are crossing the rfd_time
            p1 = (rfdData.iloc[index_p1]['offset_time'], rfdData.iloc[index_p1]['weight'])
            index_p1 = index_p1 +1
            p2 = (rfdData.iloc[index_p1]['offset_time'], rfdData.iloc[index_p1]['weight'])

            #slope = ((p2[1] - p1[1]) / (p2[0] - p1[0]))
            slope = get_slope(p1, p2)

            dt = rfd_time - p1[0]
            y_int = p1[1] + dt*slope


            rfd_slope = get_slope((0,onset), (rfd_time, y_int)) *1000
            #plot the result
            plt.subplot(2, 2, sub_plot_number)

            plt.plot((0, rfd_time), (onset, y_int),'r-', label=title + '  ' + str(rfd_slope)[:5] + ' N/s', zorder=1)
            plt.plot((rfd_time, rfd_time), (onset, maks),'k--')
            base_plot(title)

            return



        def h_interpolated(y_value, title, sub_plot_number):
            # calculates the intersection point between a horizontal line and the load curve

            index_p1 = abs(rfdData['weight'] - y_value).idxmin()
            # make sure the index is of the point below the value
            if (rfdData.iloc[index_p1]['weight'] >= y_value):
              index_p1 = index_p1 -1

            # The points of the line segment that are crossing the y_value line
            p1 = (rfdData.iloc[index_p1]['offset_time'], rfdData.iloc[index_p1]['weight'])
            index_p1 = index_p1 +1
            p2 = (rfdData.iloc[index_p1]['offset_time'], rfdData.iloc[index_p1]['weight'])


            #slope = ((p2[1] - p1[1]) / (p2[0] - p1[0]))
            slope = get_slope(p1, p2)

            dy = y_value - p1[1]
            x_int = p1[0] + dy/slope


            rfd_slope = get_slope((0,onset), (x_int, y_value)) *1000

            plt.subplot(2, 2, sub_plot_number)

            plt.plot((0, rfdData["offset_time"].iloc[-1]), (y_value, y_value),'k--')
            plt.plot((0, x_int), (onset, y_value),'r-', label=title + ' ' + str(rfd_slope)[:5]  + ' N/s', zorder=1)
            base_plot(title)
            return


        # def rfd_max(title, sub_plot_number):
        #     # calculates the steepest section of the actual curve
            # RFD max needs to be calculated from a curve fit rather than the point-to-point approach used here.
        #
        #     rfdData['dt'] = rfdData['time'] - rfdData['time'].shift(1)
        #     rfdData['dy'] = rfdData['weight'] - rfdData['weight'].shift(1)
        #
        #     rfdData['slope'] = rfdData['dy'] / rfdData['dt']
        #     rfd_max_idx = rfdData['slope'].idxmax()
        #
        #     p2 = (rfdData.iloc[rfd_max_idx]['offset_time'], rfdData.iloc[rfd_max_idx]['weight'])
        #
        #     rfd_max_idx = rfd_max_idx -1
        #     p1 = (rfdData.iloc[rfd_max_idx]['offset_time'], rfdData.iloc[rfd_max_idx]['weight'])
        #
        #     rfd_slope = get_slope(p1, p2) *1000
        #
        #     plt.subplot(2, 2, sub_plot_number)
        #
        #     plt.plot((p1[0], p2[0]), (p1[1], p2[1]),'r-', label=title + ' ' + str(rfd_slope)[:5]  + ' N/s', zorder=1)
        #     base_plot(title)
        #     return


        def rfd_20_80(lower_threshold, upper_threshold, title, sub_plot_number):
            # calculates the RFD 20%-80%
            # This function should be rewritten, the interpolation to find the points crossing 20 and 80 thresholds should be done in a septarate function.


            # calculates the intersection point between the 80% line and the load curve
            def interpolation(threshold):
                index_p1 = abs(rfdData['weight'] - threshold).idxmin()
                # make sure the index is of the point below the value
                if (rfdData.iloc[index_p1]['weight'] >= threshold):
                    index_p1 = index_p1 -1

                # The points of the line segment that are crossing the threshold line
                p1 = (rfdData.iloc[index_p1]['offset_time'], rfdData.iloc[index_p1]['weight'])
                index_p1 = index_p1 +1
                p2 = (rfdData.iloc[index_p1]['offset_time'], rfdData.iloc[index_p1]['weight'])
                slope = get_slope(p1, p2)
                dy = threshold - p1[1]
                x_interpolated = p1[0] + dy/slope
                return x_interpolated





            x_int_lower = interpolation(lower_threshold)
            x_int_upper = interpolation(upper_threshold)


            #calculate the slope of the RFD-line
            rfd_slope = get_slope((x_int_lower, lower_threshold), (x_int_upper, upper_threshold)) *1000



            plt.subplot(2, 2, sub_plot_number)

            plt.plot((0, rfdData["offset_time"].iloc[-1]), (upper_threshold, upper_threshold),'k--') #plots a horizontal line at 80%
            plt.plot((0, rfdData["offset_time"].iloc[-1]), (lower_threshold, lower_threshold),'k--') #plots a horizontal line at 20%

            plt.plot((x_int_lower, x_int_upper), (lower_threshold, upper_threshold),'r-', label=title + ' ' + str(rfd_slope)[:5]  + ' N/s', zorder=1)
            base_plot(title)
            return





        def base_plot(title):
            plt.plot(rfdData['offset_time'], rfdData['weight'],'go-', label='Load data', zorder=0)
            plt.xlim((-10, 400))
            plt.xlabel('Time [ms]')
            plt.ylabel('Load [N]')
            plt.title(title)
            #plt.plot([], [], ' ', label="Extra label on the legend"+" test")
            plt.legend(frameon=False, loc=4)
            plt.gcf().set_size_inches(10, 8)
            plt.tight_layout()
            #plt.show()

        def get_slope(p1, p2):
            slope = ((p2[1] - p1[1]) / (p2[0] - p1[0]))
            return slope

        # Convert time to ms
        rfdData['time'] = rfdData['time'] / 1000


        # discard data after max load
        maks_idx=rfdData['weight'].idxmax()
        rfdData = rfdData[:maks_idx]


        # interpolate and discard data lower than onset threshold


        index_p1 = abs(rfdData['weight'] - onset).idxmin()
        # make sure the index is of the point below the onset value
        if (rfdData.iloc[index_p1]['weight'] >= onset):
            index_p1 = index_p1 -1

        # The points of the onset line that are crossing the load curve
        p1 = (rfdData.iloc[index_p1]['time'], rfdData.iloc[index_p1]['weight'])
        index_p1 = index_p1 +1
        p2 = (rfdData.iloc[index_p1]['time'], rfdData.iloc[index_p1]['weight'])

        slope = ((p2[1] - p1[1]) / (p2[0] - p1[0]))
        dy = onset - p1[1]
        x_int = p1[0] + dy/slope


        # write the interpolated values to the p1-index
        rfdData.iloc[index_p1, rfdData.columns.get_loc('time')] = x_int
        rfdData.iloc[index_p1, rfdData.columns.get_loc('weight')] = onset



        left_filt= rfdData['weight'] < onset
        rfdData = rfdData.drop(index = rfdData[left_filt].index)
        rfdData.reset_index(drop=True, inplace=True)


        #get RFD95 value
        maks = rfdData['weight'].max()
        rfd95_line = 0.95* rfdData['weight'].max()

        rfd20_line = 0.2* rfdData['weight'].max()
        rfd80_line = 0.8* rfdData['weight'].max()

        # Correct time offset
        time_offset = rfdData.loc[0, 'time']
        rfdData['offset_time']= rfdData['time'] - time_offset


        # CALCULATION OF SUB-PLOTS
        try:
            v_interpolated(100,'RFD100ms',1)
        except:
            print('Could not calculate RFD100ms' )

        try:
            v_interpolated(200,'RFD200ms',2)
        except:
            print('Could not calculate RFD200ms' )

        try:
            h_interpolated(rfd95_line, 'RFD95%',3)
        except:
            print('Could not calculate RFD95%' )

        try:
            rfd_20_80(rfd20_line, rfd80_line, 'RFD20%-80%',4)
        except:
            print('Could not calculate RFD20-80' )



        plt.show()







    def animate(i):
        global start
        global duration

        status_bar_refresh()
        if recording == True:
            refresh_rate=50
            csv_data = pd.read_csv(csv_filename)
            a.clear()
            a.set_xlabel('Time [s]')
            a.set_ylabel('Load [kg]')
            a.set_xlim((0,duration*1000))
            a.scatter(-1000, 10)
            a.plot(csv_data['time']/1000, csv_data['weight'])
            #a.legend(['Load'])
            #a.set_title('plot title')










    ##########################################################################33


    root=Tk()
    root.title('Tindeq Progressor RFD test')
    root.geometry = ("1000x1000+10,+300")

    Grid.rowconfigure(root, 1, weight=1)
    Grid.columnconfigure(root, 1, weight=1)

    #Clear the data .tmp file upon opening the program
    csv_create()





    f= Figure(figsize=(10,5), dpi=100,tight_layout = True)
    a = f.add_subplot(111)

    canvas = FigureCanvasTkAgg(f, root)
    canvas.draw()



    toolbarFrame = Frame(master=root)
    toolbarFrame.grid(row=2,column=1, sticky=W+E)

    toolbar = NavigationToolbar2Tk(canvas, toolbarFrame)

    canvas.get_tk_widget().grid(row=1,column=1, sticky=W+E+N+S, padx=5, pady=5) #pack(side=TOP, fill=BOTH, expand = True)
    canvas._tkcanvas.grid(row=1,column=1,sticky=W+E+N+S, padx=5, pady=5)#pack(side=BOTTOM, fill=BOTH, expand = True)







    menuFrame = Frame(master=root)
    menuFrame.grid(row=1,column=0, padx=5, pady=5, sticky=N)





    button_connect = Button( menuFrame, text="Connect", width=20, height=1, command=connect)
    button_connect.grid(row=0,column=0)

    button_disconnect = Button(menuFrame, text="Disconnect", width=20, height=1, command=disconnect)
    button_disconnect.grid(row=1,column=0)

    button_tare = Button(menuFrame, state = 'active', text="Tare", width=20, height=1, command=tare)
    button_tare.grid(row=2,column=0, pady=(20,60))

    durationEntry = Entry(menuFrame, width=5)
    durationEntry.insert(END, '10')
    durationEntry.grid(row=3,column=0, stick = E)


    label = Label(menuFrame, text="Set duration [sec]:",)
    label.grid(row=3,column=0, stick=W)




    button_start = Button( menuFrame, text="Record data", width=20, height=1, command=start) #state = 'disabled',
    button_start.grid(row=4,column=0)


    #button_stop = Button(menuFrame, state = 'active', text="Cancel", width=20, height=1, command=cancel)
    #button_stop.grid(row=4,column=0)

    thresholdEntry = Entry(menuFrame, width=5)
    thresholdEntry.insert(END, '1.5')
    thresholdEntry.grid(row=6,column=0, stick = E)

    thresholdLabel = Label(menuFrame, text="RFD onset threshold:",)
    thresholdLabel.grid(row=6,column=0, stick=W)

    button_rfdCalc = Button(menuFrame, state = 'active', text="Calculate RFD", width=20, height=1, command=rfdCalc)
    button_rfdCalc.grid(row=7,column=0, pady=(0, 30))

    button_save = Button(menuFrame, state = 'active', text="Save data", width=20, height=1, command=csv_save)
    button_save.grid(row=8,column=0, sticky='S')

    status_bar = Label(root, text=status_text, bd=1, relief='sunken', anchor='w')
    status_bar.grid(row=4, columnspan=2, sticky=W+E+S,pady=(20,0))

    #animation to refresh the plot window and update status bar.
    ani = animation.FuncAnimation(f, animate, 50)

    root.mainloop()










if __name__ == '__main__':
    async_loop = asyncio.get_event_loop()
    main(async_loop)





















