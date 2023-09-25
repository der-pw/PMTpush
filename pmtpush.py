# #########################################################################################################################
# PMTpush extracts a value from a digital display (like 7 segment) in Proteus MT.
#
# Tesseract is used for the OCR method.
# Pre-compiled Windows binaries are available at the UB Mannheim https://digi.bib.uni-mannheim.de/tesseract/?C=M;O=D
#
# I have found the training data for 7 segment digits at https://github.com/Shreeshrii/tessdata_ssd
# The best results I got with ssd (best version) "-l ssd".
# #########################################################################################################################

import cv2
import pytesseract
import time
import numpy as np
from PIL import ImageGrab
import subprocess
import argparse

# user defines
wait_in_sec = 300                   # interval the main task all n seconds
upper_threshold = 400               # upper threshold that starts the monitoring
msg_threshold = 350                 # temperature at which the message should be triggered 
count = 3                           # number of messages to be sent
bbox = (1684, 274, 1806, 305)       # define captured area in bounding box (x1, y1, x2, y2)
logfile = "logging.txt"             # logfile for debug logs the recognized values as string
msg_title = "Ofentür Heißdruck"     # titel for pushover Message

trigger_activate = False
messages_sent = False
debug = False

print("PMTpush ist mit folgenden Werten gestartet!\nTriggerschwelle = " + str(upper_threshold) + "°C")
print("Message = " + str(msg_threshold) + "°C")
print("Check Intervall = " + str(wait_in_sec) + " Sekunden")
print("\nFenster darf in den Hintergrund, aber nicht schließen!\n"),

# path to Tesseract
pytesseract.pytesseract.tesseract_cmd = r'.\Tesseract-OCR\tesseract.exe'
custom_config = r'--oem 3 --psm 7 -l ssd -c tessedit_char_whitelist=0123456789'

# activate the argument parser
parser = argparse.ArgumentParser(description='Extracts the value of Temp1 from Proteus MT using OCR methods')
parser.add_argument('--debug', action='store_true', help='activates debug mode')
args = parser.parse_args()
if args.debug:
    print("Debug-Modus ist aktiviert.")
    debug = True

# function to clean the string in recognized value
def just_num(text):
    num = ''.join(filter(str.isdigit, text))
    num = num[:-2]
    return num

# print debug messages
def debug_output(message):
    if debug:
        print(message)

# function to send the pushover message
def send_msg(message, title):
    command = ["python", "./pushover/pushover-cli.py", "--config", "./pushover/p-cli.conf", message, title]

    try:
        subprocess.run(command, check=True)
        debug_output("Pushover was sent")
    except subprocess.CalledProcessError as e:
        debug_output(f"Error executing command: {e}")
    except Exception as e:
        debug_output(f"General error: {e}")


if debug:
    send_msg("Überwachung wird gestartet", msg_title)


# main task repeated
def repeat_task():
    global trigger_activate
    global messages_sent
    global count

    screenshot = ImageGrab.grab(bbox=bbox)
    image = np.array(screenshot)
    
    # load image
    #image = cv2.imread("screenshot5.png")

    # convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # erode image to make raw value thicker and denoise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 2))
    eroded_image = cv2.erode(gray, kernel, iterations=2)

    # use tesseract on the preprocessed image
    text = pytesseract.image_to_string(eroded_image, config=custom_config)
    text = text.strip() # strip leading and trailing spaces and line breaks
    
    if debug:
        cv2.imwrite("debug.png", eroded_image) 
        # output the string
        debug_output("raw String: " + text)
        with open(logfile, 'a') as file:
            file.write(text + '\n')
    
    # simple check, if the string is valid before convert it to int
    if len(text) < 4:
        value = 0
    else:
        value = int(just_num(text))
        debug_output(value)

    # if upper threshold is reached
    if value > upper_threshold and not trigger_activate:
        debug_output("Trigger is activated")
        trigger_activate = True
    
    if value < msg_threshold and trigger_activate and not messages_sent:
        debug_output("send message via pushover")
        send_msg("Temperatur liegt bei " + str(value) + "°C", msg_title)
        count = count - 1
        if count == 0:
            messages_sent = True


while True:
    repeat_task()
    time.sleep(wait_in_sec)