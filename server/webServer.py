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
import app

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

def robotCtrl(command_input, response):
    global direction_command, turn_command
    if 'forward' == command_input:
        direction_command = 'forward'
        move.move(speed_set, 'forward', 'no', rad)
    elif 'backward' == command_input:
        direction_command = 'backward'
        move.move(speed_set, 'backward', 'no', rad)
    elif 'DS' in command_input:
        direction_command = 'no'
        move.move(speed_set, 'no', 'no', rad)
    elif 'left' == command_input:
        turn_command = 'left'
        move.move(speed_set, 'no', 'left', rad)
    elif 'right' == command_input:
        turn_command = 'right'
        move.move(speed_set, 'no', 'right', rad)
    elif 'up' == command_input:
        servo.camera_ang('lookup','no')
    elif 'down' == command_input:
        servo.camera_ang('lookdown','no')

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
        RL.setColor(0,255,64)
        ap_threading=threading.Thread(target=ap_thread)   #Define a thread for data receiving
        ap_threading.setDaemon(True)                          #'True' means it is a front thread,it would close when the mainloop() closes
        ap_threading.start()                                  #Thread starts
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 10%')
        RL.setColor(0,16,50)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 30%')
        RL.setColor(0,16,100)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 50%')
        RL.setColor(0,16,150)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 70%')
        RL.setColor(0,16,200)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 90%')
        RL.setColor(0,16,255)
        time.sleep(1)
        if OLED_connection:
            screen.screen_show(2, 'AP Starting 100%')
        RL.setColor(35,255,35)
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
    global speed_set, modeSelect
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

        if isinstance(data,str):
            robotCtrl(data, response)

            if 'get_info' == data:
                response['title'] = 'get_info'
                response['data'] = [info.get_cpu_tempfunc(), info.get_cpu_use(), info.get_ram_info()]

            if 'wsB' in data:
                try:
                    set_B=data.split()
                    speed_set = int(set_B[1])
                except:
                    pass

        if not functionMode:
            if OLED_connection:
                screen.screen_show(5,'Functions OFF')
        else:
            pass

        print(data)
        response = json.dumps(response)
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
    global flask_app
    flask_app = app.webapp()
    flask_app.startthread()
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
            RL.setColor(0,80,255)
        except:
            pass
    try:
        RL.pause()
        RL.setColor(0,255,64)
        asyncio.get_event_loop().run_forever()
    except Exception as e:
        print(e)
        RL.setColor(0,0,0)
        move.destroy()
