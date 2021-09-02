#!/usr/bin/env/python3
# File name   : server.py
# Description : for FPV video and OpenCV functions
# Website     : www.adeept.com
# E-mail      : support@adeept.com
# Author      : William(Based on Adrian Rosebrock's OpenCV code on pyimagesearch.com)
# Date        : 2019/02/23

import time
import threading
import cv2
import zmq
import base64
import picamera
from picamera.array import PiRGBArray
import argparse
import imutils
from collections import deque
import psutil
import os
import servo
import PID
import LED
import datetime
from rpi_ws281x import *
import move

pid = PID.PID()
pid.SetKp(0.5)
pid.SetKd(0)
pid.SetKi(0)
Y_lock = 0
X_lock = 0
tor    = 17
FindColorMode = 0
WatchDogMode  = 0
UltraData = 3
LED  = LED.LED()

class FPV: 
    def __init__(self):
        self.frame_num = 0
        self.fps = 0

        self.colorUpper = (44, 255, 255)
        self.colorLower = (24, 100, 100)


    def SetIP(self,invar):
        self.IP = invar

    def UltraData(self,invar):
        global UltraData
        UltraData = invar


    def capture_thread(self,IPinver):
        ap = argparse.ArgumentParser()            #OpenCV initialization
        ap.add_argument("-b", "--buffer", type=int, default=64,
            help="max buffer size")
        args = vars(ap.parse_args())
        pts = deque(maxlen=args["buffer"])

        font = cv2.FONT_HERSHEY_SIMPLEX

        camera = picamera.PiCamera() 
        camera.resolution = (640, 480)
        camera.framerate = 20
        rawCapture = PiRGBArray(camera, size=(640, 480))

        context = zmq.Context()
        footage_socket = context.socket(zmq.PUB)
        print(IPinver)
        footage_socket.connect('tcp://%s:5555'%IPinver)

        avg = None
        motionCounter = 0
        #time.sleep(4)
        lastMovtionCaptured = datetime.datetime.now()

        for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            frame_image = frame.array
            cv2.line(frame_image,(300,240),(340,240),(128,255,128),1)
            cv2.line(frame_image,(320,220),(320,260),(128,255,128),1)
            timestamp = datetime.datetime.now()
            encoded, buffer = cv2.imencode('.jpg', frame_image)
            jpg_as_text = base64.b64encode(buffer)
            footage_socket.send(jpg_as_text)

            rawCapture.truncate(0)


if __name__ == '__main__':
    fpv=FPV()
    while 1:
        fpv.capture_thread('192.168.0.110')
        pass

