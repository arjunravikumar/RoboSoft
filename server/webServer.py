#!/usr/bin/env/python
# File name   : server.py
# Production  : RaspTankPro
# Website     : www.adeept.com
# Author      : William
# Date        : 2020/03/17

import time
import threading
import move
import Adafruit_PCA9685
import os
import info
import RPIservo
import servo
import robotLight
import switch
import socket
import ultra
import FPV

#websocket
import asyncio
import websockets

import json

OLED_connection = 1
try:
    import OLED
    screen = OLED.OLED_ctrl()
    screen.start()
    screen.screen_show(1, 'ADEEPT.COM')
except:
    OLED_connection = 0
    print('OLED disconnected')
    pass

functionMode = 0
speed_set = 100
rad = 0.5
turnWiggle = 60
imgLatency = 0.15

scGear = RPIservo.ServoCtrl()
scGear.moveInit()

P_sc = RPIservo.ServoCtrl()
P_sc.start()

C_sc = RPIservo.ServoCtrl()
C_sc.start()

T_sc = RPIservo.ServoCtrl()
T_sc.start()

H_sc = RPIservo.ServoCtrl()
H_sc.start()

G_sc = RPIservo.ServoCtrl()
G_sc.start()

modeSelect = 'PT'

init_pwm0 = scGear.initPos[0]
init_pwm1 = scGear.initPos[1]
init_pwm2 = scGear.initPos[2]
init_pwm3 = scGear.initPos[3]
init_pwm4 = scGear.initPos[4]

curpath = os.path.realpath(__file__)
thisPath = "/" + os.path.dirname(curpath)

def servoPosInit():
    scGear.initConfig(0,init_pwm0,1)
    P_sc.initConfig(1,init_pwm1,1)
    T_sc.initConfig(2,init_pwm2,1)
    H_sc.initConfig(3,init_pwm3,1)
    G_sc.initConfig(4,init_pwm4,1)


def replace_num(initial,new_num):   #Call this function to replace data in '.txt' file
    global r
    newline=""
    str_num=str(new_num)
    with open(thisPath+"/RPIservo.py","r") as f:
        for line in f.readlines():
            if(line.find(initial) == 0):
                line = initial+"%s" %(str_num+"\n")
            newline += line
    with open(thisPath+"/RPIservo.py","w") as f:
        f.writelines(newline)


def FPV_thread():
    global fpv
    fpv=FPV.FPV()
    fpv.capture_thread(addr[0])


def ap_thread():
    os.system("sudo create_ap wlan0 eth0 Groovy 12345678")

def robotCtrl(data):
    global direction_command, turn_command, speed_set
    if 'stop' in data["direction"]:
        direction_command = 'no'
        stopRobotMovement()
    elif 'up' == data["direction"]:
        servo.camera_ang('lookup','no')
    elif 'down' == data["direction"]:
        servo.camera_ang('lookdown','no')
    else:
        direction_command = data["direction"]
        turn_command = data["direction"]
        speed_set = data["speed"]
        move.move(data["speed"] , data["direction"], data["turn"], data["rads"])
        time.sleep(data["stopIn"])
        direction_command = 'no'
        stopRobotMovement()

def stopRobotMovement():
    move.move(0, 'no', 'no', 0.5)

def update_code():
    # Update local to be consistent with remote
    projectPath = thisPath[:-7]
    with open(f'{projectPath}/config.json', 'r') as f1:
        config = json.load(f1)
        if not config['production']:
            print('Update code')
            # Force overwriting local code
            if os.system(f'cd {projectPath} && sudo git fetch --all && sudo git reset --hard origin/master && sudo git pull') == 0:
                print('Update successfully')
                print('Restarting...')
                os.system('sudo reboot')

def wifi_check():
    try:
        s =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("1.1.1.1",80))
        ipaddr_check=s.getsockname()[0]
        s.close()
        print(ipaddr_check)
        update_code()
        if OLED_connection:
            screen.screen_show(2, 'IP:'+ipaddr_check)
            screen.screen_show(3, 'AP MODE OFF')
    except:
        RL.pause()
        RL.setColor(0,0,0)
        ap_threading=threading.Thread(target=ap_thread)   #Define a thread for data receiving
        ap_threading.setDaemon(True)                          #'True' means it is a front thread,it would close when the mainloop() closes
        ap_threading.start()                                  #Thread starts
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 10%')
        RL.setColor(0,0,0)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 30%')
        RL.setColor(0,0,0)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 50%')
        RL.setColor(0,0,0)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 70%')
        RL.setColor(0,0,0)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 90%')
        RL.setColor(0,0,0)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 100%')
        RL.setColor(0,0,0)
        if OLED_connection:
            screen.screen_show(2, 'IP:192.168.12.1')
            screen.screen_show(3, 'AP MODE ON')

async def check_permit(websocket):
    while True:
        recv_str = await websocket.recv()
        cred_dict = recv_str.split(":")
        if cred_dict[0] == "tumbler" and cred_dict[1] == "wakeup":
            response_str = "Ready to accept commands"
            await websocket.send(response_str)
            return True
        else:
            response_str = "sorry, the username or password is wrong"
            await websocket.send(response_str)

async def recv_msg(websocket):
    global speed_set, modeSelect, imgLatency
    move.setup()
    direction_command = 'no'
    turn_command = 'no'
    while True:
        response = {
            'status' : 'ok',
            'title' : '',
            'data' : None,
            'dist': ultra.checkdist()
        }

        data = ''
        data = await websocket.recv()
        try:
            data = json.loads(data)
        except Exception as e:
            print('not A JSON')

        if not data:
            continue
        response["recieverLatency"] = (time.time() * 1000) - data["requestTime"]
        if 'mobility' == data["type"]:
            robotCtrl(data)

        elif 'get_info' == data["type"]:
            response['title'] = 'get_info'
            response['data'] = [info.get_cpu_tempfunc(), info.get_cpu_use(), info.get_ram_info()]

        if not functionMode:
            if OLED_connection:
                screen.screen_show(5,'Functions OFF')
        else:
            pass

        print(data)
        response["requestTime"] = data["requestTime"]
        response["responseTime"] = time.time() * 1000
        response = json.dumps(response)
        time.sleep(imgLatency)
        await websocket.send(response)

async def main_logic(websocket, path):
    await check_permit(websocket)
    await recv_msg(websocket)

if __name__ == '__main__':
    switch.switchSetup()
    switch.set_all_switch_off()

    HOST = ''
    PORT = 10223                              #Define port serial 
    BUFSIZ = 1024                             #Define buffer size
    ADDR = (HOST, PORT)

    try:
        RL=robotLight.RobotLight()
        RL.start()
        RL.breath(70,70,255)
    except:
        print('Use "sudo pip3 install rpi_ws281x" to install WS_281x package\n"sudo pip3 install rpi_ws281x" rpi_ws281x')
        pass

    while  1:
        wifi_check()
        try:                  #Start server,waiting for client
            start_server = websockets.serve(main_logic, '0.0.0.0', 8888)
            asyncio.get_event_loop().run_until_complete(start_server)
            print('waiting for connection...')
            break
        except Exception as e:
            print(e)
            RL.setColor(0,0,0)

        try:
            RL.setColor(0,0,0)
        except:
            pass
    try:
        RL.pause()
        RL.setColor(0,0,0)
        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print(e)
        RL.setColor(0,0,0)
        move.destroy()
