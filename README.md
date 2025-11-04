# ENVOI_to_BRINK_Caller_ID
This allows merchants using Brink POS and ENVOI VOIP to have caller ID info show up in Brink. Since the ENVOI API is not public I have redacted the endpoint.
This program was compiled to a Windows .exe and ran that way.

ESS Caller ID interface between ENVOI VOIP and Brink
Robert Hill
12/19/2022
Written in Python 3.8
.py script requires the modules pyserial and requests be installed
The exe bundles everything so you don't even need to install python

To use this Simply copy the ESSCallerID folder to the machine at C:\\users\<current user>\
the program will create this folder and the ini anyway but this keeps the exe in the same place.  
Open the ini and set the store phone number and the COM port to be used.  Run the exe.



Use the file Null Modem Link Cable (CID).docx to create a cable to link the COM port of the software to
the COM port that Brink is using.

V1 was written to use extension numbers to map calls to specific phone lines
V2 was written to manage call lines when all calls come under the same extension number.
V2.1. reduced the number of COM transmissions
V2.1.2 compiled new exe that doesn't launch a cmd window
