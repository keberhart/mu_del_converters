#!/usr/bin/env python

#
#   A class to control mu-del converters
#
#   Incomplete
#   7DEC11 - Kyle Eberhart

import telnetlib
import logging
from multiprocessing import Process
from multiprocessing import Queue as Q
import queue
import time


class ConvProcess(object):
    '''
    A converter controller that runs in a seperate process, for smoother
    GUI operation. in_queue is how you send commands, out_queue is where
    data comes back.
    '''

    def __init__(self, **kwargs):
        '''
        Initialize our queues and other startup tasks.
        '''
        self.in_queue = Q()
        self.out_queue = Q()
        self.process = None
        self.address = kwargs.get('address', None)
        self.port = kwargs.get('port', None)
        self.converter_target = None

    def connect(self):
        '''
        start the converter communication process, feed it some queues.
        '''
        self.process = Process(target=self._connect,
                               args=(self.in_queue,
                                     self.out_queue))
        self.process.daemon = 1
        self.process.start()

    def command(self, message):
        '''
        send a command to the converter, using the in_q.
        '''
        self.in_queue.put(message)

    def disconnect(self):
        '''
        disconnect from the converter and terminate the process.
        '''
        self.in_queue.put('disconnect')

    def kill_process(self):
        '''
        kill the child process.
        '''
        self.in_queue.put('kill')
        self.process.join()
        self.process = None
        self.converter_target = None

    def _connect(self, in_q, out_q):
        '''
        The converter connection and processing loop.
        '''
        self.converter_target = Converter(address=self.address,
                                          port=self.port)
        self.converter_target.connect()
        while True:
            try:
                conv_command = in_q.get_nowait()
                if conv_command == 'disconnect':
                    self.converter_target.disconnect()
                    out_q.put("Requesting converter process termination.")
                elif conv_command == 'kill':
                    break
                elif 'freq' in conv_command:
                    self.converter_target.setFreq(conv_command[1])
                elif 'atten' in conv_command:
                    self.converter_target.setAtten(conv_command[1])
                elif 'mute' in conv_command:
                    if conv_command[1]:
                        self.converter_target.setMute()
                    else:
                        self.converter_target.unsetMute()
            except Queue.Empty:
                try:
                    if self.converter_target is not None:
                        self.converter_target.getStatus()
                        out_q.put({'freq' : self.converter_target.frequency,
                                   'atten' : self.converter_target.attenuation,
                                   'status' : self.converter_target.statusCode,
                                   'mute' : self.converter_target.mute})
                except EOFError:
                    out_q.put("Status attempt failed!")
                    self.converter_target.disconnect()
                    out_q.put("Requesting converter process termination.")
            time.sleep(1)

    def __del__(self):
        '''
        clean up correctly if possible.
        '''
        if self.process:
            self.disconnect()
            self.kill_process()


class Converter(object):

    def __init__(self, address='192.168.1.3', port=4004):
        self.logger = logging.getLogger(__name__)
        self.address = address
        self.port = port
        self.target = None
        self.errorMsg = None

    def __repr__(self):
        return "<MuDelConverter('%s', '%s')" % (self.address, self.port)

    def connect(self):
        '''
        connect to the converter, and determine the converter type
        '''
        self.target = telnetlib.Telnet(self.address, self.port)
        self.target.write('<?\r'.encode('ascii'))
        self.status = self.target.read_until(b'randomString', 2).decode('ascii')

        if 'MDC-1627F1K-7' in self.status:
            self.type = 'MDC-1627F1K-7'
        elif 'MDC-2125F1K-72' in self.status:
            self.type = 'MDC-2125F1K-72'
        elif 'MUC-7-1627-F1K' in self.status:
            self.type = 'MUC-7-1627-F1K'
        else:
            self.errorMsg = "Converter model unknown: %s" % self.status
            self.logger.debug(self.errorMsg)
            raise RuntimeError(self.errorMsg)

    def disConnect(self):
        '''
        disconnect from the converter
        '''
        self.target.close()
        self.target = None

    def getStatus(self):
        if self.target is None:
            self.connect()
        self.target.write('<S\r'.encode('ascii'))
        self.status = self.target.read_until(b'SomeCrazyString', 2).decode('ascii')
        if self.type == 'MDC-1627F1K-7' or self.type == 'MUC-7-1627-F1K':
            myStatus = self.status[1:].split(',')
            self.frequency = (float(myStatus[0]) + 1600000) / 1000
            self.attenuation =  (float(myStatus[1]) / 5)
            if int(myStatus[2]) is 1:
                self.statusCode = "Normal Operation"
            elif int(myStatus[2]) is 2:
                self.statusCode = "Synth Lock Lost"
            elif int(myStatus[2]) is 3:
                self.statusCode = "Synth 2 Lock Lost"
            elif int(myStatus[2]) is 4:
                self.statusCode = "Synth 3 Lock Lost"
            elif int(myStatus[2]) is 5:
                self.statusCode = "Local Osc Lock Lost"
            elif int(myStatus[2]) is 6:
                self.statusCode = "Aux Input 2 Alarm"
            elif int(myStatus[2]) is 7:
                self.statusCode = "Aux Input 3 Alarm"
            elif int(myStatus[2]) is 8:
                self.statusCode = "Aux Input 4 Alarm"
            elif int(myStatus[2]) is 9:
                self.statusCode = "Reference Osc Lost"
            else:
                self.statusCode = "Unknown"
            self.mute = bool(int(myStatus[3][0:1]))

        if self.type == 'MDC-2125F1K-72':
            myStatus = self.status[1:].split(',')
            self.frequency = (float(myStatus[0]) + 2100000) / 1000
            self.attenuation =  (float(myStatus[1]) / 5)
            if int(myStatus[2]) is 1:
                self.statusCode = "Normal Operation"
            elif int(myStatus[2]) is 2:
                self.statusCode = "Synth Lock Lost"
            elif int(myStatus[2]) is 3:
                self.statusCode = "Synth 2 Lock Lost"
            elif int(myStatus[2]) is 4:
                self.statusCode = "Synth 3 Lock Lost"
            elif int(myStatus[2]) is 5:
                self.statusCode = "Local Osc Lock Lost"
            elif int(myStatus[2]) is 6:
                self.statusCode = "Aux Input 2 Alarm"
            elif int(myStatus[2]) is 7:
                self.statusCode = "Aux Input 3 Alarm"
            elif int(myStatus[2]) is 8:
                self.statusCode = "Aux Input 4 Alarm"
            elif int(myStatus[2]) is 9:
                self.statusCode = "Reference Osc Lost"
            else:
                self.statusCode = "Unknown"
            self.mute = None

        return {'Freq': self.frequency, 'Atten': self.attenuation, 'Code': self.statusCode, 'Mute': self.mute}

    def setFreq(self, freq):
        '''
        set the converter frequency
        '''
        if self.target is None:
            self.connect()
        if self.type == 'MDC-1627F1K-7' or self.type == 'MUC-7-1627-F1K':
            stepValue = (int((float(freq) * 1000)) - 1600000)
            if stepValue < 0:
                stepValue = 0
            if stepValue > 1100000:
                stepValue = 1100000
            self.target.write('<X1{}\r'.format(stepValue).encode('ascii'))
            self.target.read_until(b'SomeCrazyString', 2).decode('ascii')
        elif self.type == 'MDC-2125F1K-72':
            stepValue = (int((float(freq) * 1000)) - 2100000)
            if stepValue < 0:
                stepValue = 0
            if stepValue > 400000:
                stepValue = 400000
            self.target.write('<{}\r'.format(stepValue).encode('ascii'))
            self.target.read_until(b'SomeCrazyString', 2).decode('ascii')
        else:
            self.errorMsg = "Unknown converter type, no freq change"
            self.logger.debug(self.errorMsg)
            raise RuntimeError(self.errorMsg)

    def setAtten(self, atten):
        if self.target is None:
            self.connect()
        if self.type == 'MDC-1627F1K-7' or self.type == 'MUC-7-1627-F1K':
            stepValue = int(float(atten) * 5)
            if stepValue < 0:
                stepValue = 0
            if stepValue > 150:
                stepValue = 150
            self.target.write('<A1{}\r'.format(stepValue).encode('ascii'))
            self.target.read_until(b'SomeCrazyString', 2).decode('ascii')
        elif self.type == 'MDC-2125F1K-72':
            stepValue = int(float(atten) * 5)
            if stepValue < 0:
                stepValue = 0
            if stepValue > 150:
                stepValue = 150
            self.target.write('<A{}\r'.format(stepValue).encode('ascii'))
            self.target.read_until(b'SomeCrazyString', 2).decode('ascii')
        else:
            self.errorMsg = "Unknown converter type, no atten change"
            raise RuntimeError(self.errorMsg)

    def setMute(self):
        if self.target is None:
            self.connect()
        if self.type == 'MDC-2125F1K-72':
            self.errorMsg = "This D/C doesn't support muting"
            raise RuntimeError(self.errorMsg)
        self.target.write('<M1\r'.encode('ascii'))
        self.target.read_until(b'SomeCrazyString', 2).decode('ascii')

    def unsetMute(self):
        if self.target is None:
            self.connect()
        if self.type == 'MDC-2125F1K-72':
            self.errorMsg = "This D/C doesn't support muting"
            raise RuntimeError(self.errorMsg)
        self.target.write('<M0\r'.encode('ascii'))
        self.target.read_until(b'SomeCrazyString', 2).decode('ascii')

    def setConfig(self, **kwargs):
        '''
        configure the whole converter in one bang
        '''
        if 'Freq' in kwargs:
            self.setFreq(kwargs['Freq'])
        if 'Atten' in kwargs:
            self.setAtten(kwargs['Atten'])
        if 'Mute' in kwargs:
            if kwargs['Mute'] is True:
                self.setMute()
            if kwargs['Mute'] is False:
                self.unsetMute()

    def close(self):
        if self.target is not None:
            self.disConnect()


if __name__ == "__main__":
    # run a test, or just set things up...
    import argparse
    import sys

    logging.basicConfig(filename='Mudelconverter.log',
                        filemode='w',
                        level=logging.INFO)

    parser = argparse.ArgumentParser(description='Configure a MuDel Converter',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-f', '--freq', help='Set the frequency in MHz.')
    parser.add_argument('-a', '--atten', help='Set the attenuation in dB.')
    parser.add_argument('-m', '--mute', help='Toggle the mute.')
    parser.add_argument('dest', help='IP address of the target device.')
    args = parser.parse_args()
    config = vars(args)

    if config['dest'] is not None:
        try:
            ip, port = config['dest'].split(':')
        except ValueError as err:
            print('\nIt doesn\'t seem like a port was specified.')
            print('\txxx.xxx.xxx.xxx:ppp')
            print('Where xxx is the IP octet and ppp is the port number.\n')
            sys.exit()
        try:
            converter = Converter(ip, port)
            converter.connect()
            print('\n')
#            print(converter.status)
        except RuntimeError as err:
            print('\nConnection to converter failed!!!')
            print(err)
            print('\n')
            sys.exit()
        try:
            converter.getStatus()
            print('---- Current Status ----')
            print('Freq:  {} MHz'.format(converter.frequency))
            print('Atten: {} dB'.format(converter.attenuation))
            print('LO:    {}'.format(converter.statusCode))
            print('Mute:  {}'.format(converter.mute))
            print('\n')
        except RuntimeError as err:
            print('\nStatus fetch failed!!!')
            print(err)
            print('\n')
            sys.exit()

    if config['freq'] is not None:
        # set the frequency, check the input formatting first.
        converter.setFreq(config['freq'])

    if config['atten'] is not None:
        # set the attenuation, check the input formatting first.
        converter.setAtten(config['atten'])

    if config['mute'] is not None:
        # always unmute the converter.
        converter.unsetMute()

    converter.getStatus()
    print('---- Final Status ----')
    print('Freq:  {} MHz'.format(converter.frequency))
    print('Atten: {} dB'.format(converter.attenuation))
    print('LO:    {}'.format(converter.statusCode))
    print('Mute:  {}'.format(converter.mute))
    print('\n')

    converter.close()
    sys.exit()


