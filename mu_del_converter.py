#!/usr/bin/env python

#
#   A class to control mu-del converters
#
#   Incomplete
#   7DEC11 - Kyle Eberhart

import telnetlib
import logging

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
        self.target.write('<?\r')
        self.status = self.target.read_until('randomString', 1)

        if 'MDC-1627F1K-7' in self.status:
            self.type = 'MDC-1627F1K-7'
        elif 'MDC-2125F1K-72' in self.status:
            self.type = 'MDC-2125F1K-72'
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
        self.target.write('<S\r')
        self.status = self.target.read_until('SomeCrazyString', 1)
        if self.type == 'MDC-1627F1K-7':
            myStatus = self.status[1:].split(',')
            self.frequency = (int(myStatus[0]) + 1600000) / 1000
            self.attenuation =  (int(myStatus[1]) / 5)
            if myStatus[2] == '1':
                self.statusCode = "NormalOperation"
            elif myStatus[2] == '2':
                self.statusCode = "SynthLockLost"
            elif myStatus[2] == '3':
                self.statusCode = "Synth2LockLost"
            elif myStatus[2] == '4':
                self.statusCode = "Synth3LockLost"
            elif myStatus[2] == '5':
                self.statusCode = "LocalOscLockLost"
            elif myStatus[2] == '6':
                self.statusCode = "AuxInput2Alarm"
            elif myStatus[2] == '7':
                self.statusCode = "AuxInput3Alarm"
            elif myStatus[2] == '8':
                self.statusCode = "AuxInput4Alarm"
            elif myStatus[2] == '9':
                self.statusCode = "ReferenceOscLost"
            else:
                self.statusCode = "Unknown"
            if myStatus[3] == '1':
                self.mute = True
            else:
                self.mute = False

        if self.type == 'MDC-2125F1K-72':
            myStatus = self.status[1:].split(',')
            self.frequency = (int(myStatus[0]) + 2100000) / 1000
            self.attenuation =  (int(myStatus[1]) / 5)
            if myStatus[2] == '1':
                self.statusCode = "NormalOperation"
            elif myStatus[2] == '2':
                self.statusCode = "SynthLockLost"
            elif myStatus[2] == '3':
                self.statusCode = "Synth2LockLost"
            elif myStatus[2] == '4':
                self.statusCode = "Synth3LockLost"
            elif myStatus[2] == '5':
                self.statusCode = "LocalOscLockLost"
            elif myStatus[2] == '6':
                self.statusCode = "AuxInput2Alarm"
            elif myStatus[2] == '7':
                self.statusCode = "AuxInput3Alarm"
            elif myStatus[2] == '8':
                self.statusCode = "AuxInput4Alarm"
            elif myStatus[2] == '9':
                self.statusCode = "ReferenceOscLost"
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
        if self.type == 'MDC-1627F1K-7':
            stepValue = (int((float(freq) * 1000)) - 1600000)
            if stepValue < 0:
                stepValue = 0
            if stepVaule > 1100000:
                stepValue = 1100000
            self.target.write('<X%s\r' % stepValue)
        elif self.type == 'MDC-2125F1K-72':
            stepValue = (int((float(freq) * 1000)) - 2100000)
            if stepValue < 0:
                stepValue = 0
            if stepValue > 400000:
                stepVaule = 400000
            self.target.write('<%s\r' % stepValue)
        else:
            self.errorMsg = "Unknown converter type, no freq change"
            self.logger.debug(self.errorMsg)
            raise RuntimeError(self.errorMsg)

    def setAtten(self, atten):
        if self.target is None:
            self.connect()
        if self.type == 'MDC-1627F1K-7':
            stepValue = (int(atten) * 5)
            if stepValue < 0:
                stepValue = 0
            if stepVaule > 150:
                stepValue = 150
            self.target.write('<A1%s\r' % stepValue)
        elif self.type == 'MDC-2125F1K-72':
            stepValue = (int(atten) * 5)
            if stepValue < 0:
                stepValue = 0
            if stepValue > 150:
                stepVaule = 150
            self.target.write('<A%s\r' % stepValue)
        else:
            self.errorMsg = "Unknown converter type, no atten change"
            raise RuntimeError(self.errorMsg)

    def setMute(self):
        if self.target is None:
            self.connect()
        if self.type == 'MDC-2125F1K-72':
            self.errorMsg = "This D/C doesn't support muting"
            raise RuntimeError(self.errorMsg)
        self.target.write('<M1\r')

    def unsetMute(self):
        if self.target is None:
            self.connect()
        if self.type == 'MDC-2125F1K-72':
            self.errorMsg = "This D/C doesn't support muting"
            raise RuntimeError(self.errorMsg)
        self.target.write('<M0\r')

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
