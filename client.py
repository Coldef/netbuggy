"""
The client program. Reads USB joystick inputs (PS3 controller) and sends it to the client program running on RPi.
"""

from inputs import devices
from inputs import get_gamepad
import socket

ADDR = "192.168.1.101"
PORT = 1337


def main():

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    pads = devices.gamepads
    print("found: {}".format(pads[0]))  # look for gamepads

    if len(pads) == 0:
        raise Exception("Couldn't find any Gamepads!")

    rx = 0  # right stick horizontal
    ry = 0  # right stick vertical
    x = 0  # left stick horizontal
    y = 0  # left stick bertical
    b = 0  # R1

    while True:
        events = get_gamepad()  # in each loop, read the gamepad's button states

        for event in events:
            # print(event.ev_type, event.code, event.state)
            if event.code == "ABS_RX":
                # if the event includes update to right stick horizontal, write the state to the variable
                rx = event.state
            elif event.code == "ABS_RY":
                ry = event.state
            elif event.code == "ABS_X":
                x = event.state
            elif event.code == "ABS_Y":
                y = event.state
            elif event.code == "BTN_TR":
                b = event.state
        print("x: {:3}, y: {:3}, rx: {:3}, ry: {:3}, b: {}".format(x, y, rx, ry, b))

        # send 3 bytes: b, x, ry. in binary bbbbbbbb xxxxxxxx yyyyyyyy
        joined = (x & 255) << 8 | (ry & 255) | b << 16  # join all the data into 1 integer and..
        msg = joined.to_bytes(8, 'big')  # turn the integer into bytes object (in big endian) and send it.
        '''
        The message in binary form looks like this (has 5 redundant bytes):
        
        00000000 00000000 00000000 00000000 00000000 0000000b xxxxxxxx yyyyyyyy
        
        where b is the boost button (R1). It can only be 1 or 0, so it requires 1 bit.
        x byte contains data for left stick (0 - 255) (256 different numbers can be presented in 8 bits)
        y byte contains data for right stick (0 - 255)
        '''

        print("sending {}".format(msg))
        try:
            s.sendto(msg, (ADDR, PORT))
        except ConnectionRefusedError:
            # if sending failed, don't worry, try again.
            print("Connection refused")


main()
