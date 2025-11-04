# This script gets current call data from ENVOI API 
# to feed to BRINK for caller ID
# Robert Hill
# for ESS
# 12/19/2022
# python v 3.8
# must install pyserial, requests, psutil modules
#====================================================================================================================
#Change Log
# 01/06/2023    Added logic to only allow one instance to run at a time
# 05/18/2023    Added logic to keep more than 4 phone calls from crashing the program
# 06/22/2023    Added logic to only run between 9am and 10 PM
#               Added logic to restart itself if it get the "Max retries" error
#V 2.2.2

# get needed modules
import json
import requests
from datetime import datetime
import sys
import os
from os.path import exists
import serial
import time
import configparser
import psutil
import subprocess

# prevent multiple instances running
processName = 'ESS_CallerID.exe'
processCounter = 0
for p in psutil.process_iter(attrs=['name']):
    if processName in p.name():
        processCounter += 1
if processCounter > 2:
    sys.exit(1)

# setup our paths
PATH = os.path.expanduser('~')
programPath = PATH + '\ESSCallerID'
if not os.path.exists(programPath):
    os.makedirs(programPath)
INIFILE = r'\ESSCallerID.ini'
INIPATH = programPath + INIFILE
LOGFILE = r'\ENVOI_API_LOG.txt'

# special error message
MAX_RETRY_ERROR = "OS error: HTTPConnectionPool(host='portal.envoi.com', port=80): Max retries exceeded with url:"

# write/read our ini file
config = configparser.ConfigParser()

if not exists(INIPATH):
    config['STORENUMBER'] = {'storenum':'00000000'}
    config['COMPORT'] = {'portnum': 'COM3', 'baud': '2400'}
    config['ACCOUNT'] = {'username':'0000000', 'password':'00000000'}
    with open(INIPATH,'w') as configfile:
        config.write(configfile)
config.read(INIPATH)

# settings
USERNAME= config['ACCOUNT']['username']
PASSWORD= config['ACCOUNT']['password']
URL= <API URL HERE> /?auth_username='+USERNAME+'&auth_password='+PASSWORD + '&direction=in'
STORE_PHONE_NUMBER = config['STORENUMBER']['storenum']
COMPORT = config['COMPORT']['portnum']
BAUD = config['COMPORT']['baud']

# manage active lines
activeLines = {1:False, 2:False, 3:False, 4:False}
activeCalls = {1:0, 2:0, 3:0, 4:0}

def restartService():
    if os.path.exists(programPath + '\restartcallerid.bat'):
        batFileName = r'\restartcallerid.bat' 
        subprocess.call([ programPath + batFileName])

def logEvent(data):
    # create/open our log FILE 
    try:
        log = open(programPath + LOGFILE,'a')
        dtNow = datetime.now()
        now = str(dtNow.strftime('%m-%d-%Y %H:%M:%S'))
        log.write(now + '\n')
        log.write(data)
        log.close()
        if data[0:94] == MAX_RETRY_ERROR:
            restartService()
    except OSError as err:
        print("OS error: {0}".format(err))
        sys.exit(1)

# This function tells brink to hang up any lines not in use
def setActiveLines(callList):
    for call in activeCalls:
        if call > 4:
            break;
        if activeCalls[call] not in callList and activeLines[call]:
            try:
                ser = serial.Serial(COMPORT,BAUD)
                ser.write(bytearray('+2,0,' + str(call) + '\r\n',  'ascii'))
                ser.close()
                activeLines[call] = False
                activeCalls[call] = 0
            except OSError as err:
                print("OS error: {0}".format(err))
                logEvent("OS error: {0}".format(err))

# This function makes the API call to ENVOI
def getCallData(): 
    try:
        r = requests.get(URL)
        callData = r.json()
        parseCallData(callData)
    except OSError as err:
        print("OS error: {0}".format(err))
        logEvent("OS error: {0}".format(err))

# This function will send called id info to Brink
def sendToBrink(CIDData):
    try:
        ser = serial.Serial(COMPORT,BAUD)
        ser.write(bytearray(CIDData, 'ascii'))
        ser.close()
    except OSError as err:
        print("OS error: {0}".format(err))
        logEvent("OS error: {0}".format(err))

# This function will get the next free line number from the activeLines array   
def getAvailableLineNum():
    lineNum = None
    for actline in activeLines:
        if not activeLines[actline]:
            lineNum = actline
            break;
        if lineNum is None:
            lineNum = 5
    return lineNum

# This function loops through the calls returned from the ENVOI API.  We get all customer calls
def parseCallData(callData):
# first check that we get a valid response from the API
    for response in callData['responses']:
        respCode = int(response['code'])
        
    if respCode == 200:
        callList=[]             # initialize callList which holds the uniqueID for all active calls after each API request
        for call in callData['data']:
            callExists = False  # initialize 
            #this is to make sure we are only getting answered calls for the store we want.
            if int(call['answered']) > 0 and str(call['cnumber']) == STORE_PHONE_NUMBER:
                calledNumber = str(call['cnumber'])
                extension = str(call['dnumber'])
                callerName = str(call['callername_external']).replace(',',' ')
                callerPhone = str(call['callerid_external'])
                uniqueID = str(call['uniqueid'])
                sourceType = str(call['stype'])
                #CHANGE TO LOGGING
                print( '******INCOMING CALL *************')
                print( calledNumber + '\n' + extension + '\n' + callerName + '\n' + callerPhone + '\n' + uniqueID + '\n' + sourceType)
                # get the next available line
                for activeCall in activeCalls:
                    if activeCalls[activeCall] == float(uniqueID):
                        callExists = True
                        callList.append(float(uniqueID))
                if not callExists:
                    lineNumber = getAvailableLineNum()
                    # Brink can only handle 4 lines.  Any more active calls we drop until there is a free line.
                    if lineNumber > 4:
                        break;
                    activeLines[lineNumber] = True
                    CIDData = '+1,' + callerPhone +',' + callerName + ',' + str(lineNumber) + '\r\n'
                    print(CIDData)
                    # gather unique id's
                    callList.append(float(uniqueID))
                    activeCalls[lineNumber] =  float(uniqueID)
                    sendToBrink(CIDData)
        setActiveLines(callList)
        
    else:
        logEvent('API responded with: ' + str(callData))
                    
logEvent('START PROGRAM V 2.2.2: ************' + '\n')
while True:
    c_time = datetime.now().strftime("%H:%M:%S")
    if c_time > '09:00:00' and c_time < '22:00:00':
        getCallData()
        time.sleep(5)
    else:
        time.sleep(60)

log.close()
