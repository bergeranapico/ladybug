# Import VISA frontend
import pyvisa as visa
# Import modules
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
import csv
import tkinter
from tkinter import filedialog

# define serial number of Ladybug sensor
ser_lb = '177465'
print('Serienummer des LB5940L ist: ' + ser_lb)

# Inputs vom User sammeln
IP = input('IP-Adresse DUT eingeben (z.B. 192.168.1.196): ')
# ser_lb = input('Seriennummer vom Ladybug 5940L eingeben (z.B. 177465): ')
power = input('gewünschten Leistungspegel [dBm] eingeben (z.B. 0) oder "min" bzw. "max" eingeben: ')
if not power == 'max' or power == 'min':
    power = float(power)
steps = input('Anzahl Frequenzschritte eingeben (z.B. 50): ')
ave = input('Anzahl Mittelungen vom Ladybug 5940L eingeben (z.B. 2): ')
print('\n')

# Activate the standard IVI backend
rm = visa.ResourceManager()
# Activate for using pure Python backend ('PyVISA-py' must be installed)
# rm = visa.ResourceManager('@py')
# List all stored devices in the backend
# res=rm.list_resources()
# print(res)

# establish connection to the devices
lb = rm.open_resource('USB0::0x1A0D::0x15D8::' + ser_lb + '::1::INSTR')
dut = rm.open_resource('TCPIP0::' + IP + '::inst0::INSTR')

# create idn list of the used devices and print it out
# idn = []
# idn.append(lb.query('*IDN?'))
# idn.append(apsin.query('*IDN?'))
# print(idn)

# initialize ladybug
lb.read_termination = '\n'
lb.write_termination = '\n'
lb.timeout = 6000
lb.write('*CLS')  # clear the error queue
lb.write('syst:pres def')  # set to the default settings
lb.query('*OPC?')  # wait for commands before, to be completed
lb.write('aver:coun:auto off')  # turn off automatic averaging
lb.write('sens:aver:sdet off')  # turn off step detection
lb.write('init:cont off')  # turn off continuous triggering, necessary to allow "read?"" to start
lb.write('sens:aver:coun ' + str(ave))  # average over the desired amount of values
err_lb = lb.query('syst:err?')
lb.query('*OPC?')
print('ladybug error: ' + err_lb)

# initialize device
dut.read_termination = '\n'
dut.write_termination = '\n'
dut.write('*CLS')  # clear the error queue
dut.write('syst:pres')  # set to the default settings
dut.query('*OPC?')  # wait for commands before, to be completed
dut.write('POW:MODE CW')  # select the power mode CW
err_dut = dut.query('syst:err?')
dut.query('*OPC?')
print('DUT error: ' + err_dut)
print('\n')

# query frequency and power ranges
f_low_dut = float(dut.query('freq? min'))
f_high_dut = float(dut.query('freq? max'))
f_low_lb = float(lb.query('serv:sens:freq:min?'))
f_high_lb = float(lb.query('serv:sens:freq:max?'))
p_low_dut = float(dut.query('pow? min'))
p_high_dut = float(dut.query('pow? max'))
p_low_lb = float(lb.query('serv:sens:pow:usab:min?'))
p_high_lb = float(lb.query('serv:sens:pow:usab:max?'))

# define frequency range
if f_low_lb <= f_low_dut:
    print('untere Frequenz durch DUT limitiert')
    f_low = f_low_dut
else:
    print('untere Frequenz durch LB5940L limitiert')
    f_low = f_low_lb

if f_high_lb >= f_high_dut:
    print('obere Frequenz durch DUT limitiert')
    f_high = f_high_dut
else:
    print('obere Frequenz durch LB5940L limitiert')
    f_high = f_high_lb

print('\n')

# generate frequency vector
freq = np.linspace(f_low, f_high, int(steps))

# initialize power and time vector
p = []
t = []

# check power input of user, avoid damage of LB5940L
if isinstance(power, (int, float)) and not p_low_lb <= power <= p_high_lb:
    print('Abbruch: Leistung ausserhalb des Messbereichs vom LB5940L!')
    exit()

# set power if 'max' or 'min' is set by user
if power == 'max':
    power = p_high_dut
elif power == 'min':
    power = p_low_dut

# define power range
if p_low_lb <= p_low_dut:
    print('untere Leistungsgrenze durch DUT limitiert')
    p_low = p_low_dut
else:
    print('untere Leistungsgrenze durch LB5940L limitiert')
    p_low = p_low_lb

if p_high_lb >= p_high_dut:
    print('obere Leistungsgrenze durch DUT limitiert')
    p_high = p_high_dut
else:
    print('obere Leistungsgrenze durch LB5940L limitiert')
    p_high = p_high_lb

print('\n')

dut.write('POW ' + str(power))  # set the power level in dBm
dut.write('OUTP ON')  # activate the rf output

# define measurement procedure
i = 0
# define the number of repetitions of the measurement procedure
rep = 1
for x in range(rep):
    for f in freq:
        dut.write('freq ' + str(f))
        dut.query('*OPC?')
        lb.write('freq ' + str(f))
        lb.query('*OPC?')
        if i == 0:
            sleep(0.1)  # too avoid problem with first measurement being too low
        p.append(float(lb.query('read?')))
        print(p[i])
        i += 1

# multiply frequency vector
freqn = list(freq)*rep
# deactivate the rf output
dut.write('OUTP OFF')

# close visa connections
lb.close()
dut.close()

# store data to csv-file
formats = [('Comma Separated values', '*.csv')]
root = tkinter.Tk()
filename = filedialog.asksaveasfilename(parent=root, filetypes=formats, title="Save as ...")

header = ['freq [Hz]', 'power [dBm]']
rows = [list(a) for a in zip(freqn, p)]

if filename:
    with open(filename, 'w', newline='') as file:
        write = csv.writer(file)
        write.writerow(header)
        write.writerows(rows)

# plot the result
plt.plot(freqn, p)
plt.xlabel('freq [Hz]')
plt.ylabel('power [dBm]')
plt.grid(True)
# plt.xscale('log')
plt.show()
