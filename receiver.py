import socket
import pigpio

pi = pigpio.pi()  # use local pi's hardware PWM

ADDR = "192.168.1.101"
PORT = 1337


# 50Hz
# pw of 1ms = 0%
# pw of 1.5ms = 50%
# pw of 2ms = 100%

def valmap(value, lstart, lstop, rstart, rstop):
    lspan = lstop - lstart
    rspan = rstop - rstart

    valueScaled = float(value - lstart) / float(lspan)

    return int(rstart + (valueScaled * rspan))


def main():
    SERVO = 13  # servo pin
    MOTOR = 12  # motor pin
    pi.set_PWM_frequency(MOTOR, 50)  # max pulse width = 20ms. 50Hz is required by the ESC
    pi.set_PWM_frequency(SERVO, 50)
    pi.set_PWM_range(MOTOR, 20000)  # 20ms / 20000 = 0.001ms (resolution)
    pi.set_PWM_range(SERVO, 2000)  # 20ms / 2000 = 0.01ms
    pi.set_mode(MOTOR, pigpio.ALT0)  # PWM mode
    pi.set_mode(SERVO, pigpio.ALT0)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4 UDP
    s.settimeout(1)  # 1 second timeout for failsafe
    try:
        s.bind((ADDR, PORT))
    except Exception as e:
        print("can't bind address: {}".format(e))
        exit()
    print("UDP socket ready on {}:{}".format(s.getsockname()[0], s.getsockname()[1]))

    while True:
        try:
            msg, adr = s.recvfrom(8)  # could also use just 3 bytes
            msg = int.from_bytes(msg, 'big')  # turn the bytes into ints

            '''
            Of the 8 bytes received, I use only 3 least significant
            ones. The format for the 3 bytes is as follows:

            0000 000b  xxxx xxxx  yyyy yyyy

            The first byte can only be 1 or 0 because the boost button
            has only 2 states.
            The second byte (x) contains 8-bit number representing
            the state of the left stick.
            The last byte (y) contains 8-bit number representing
            the state of the right stick.

            b (for boost) bound currently to R1. Allows the use of whole
            power range of the motor when held.

            x is left stick's horizontal movement.

            y is right stick's vertical movement. Raw data gives full
            input when the stick is down, so I inverted it as it feels
            natural to have higher values when held up.
            '''

            b = (msg & 65536) >> 16  # b 00000000 00000000
            x = (msg & 65280) >> 8  # 0 xxxxxxxx 00000000
            y = 255 - (msg & 255)  # 0 00000000 yyyyyyyy

            multiplier = 1
            if (b == 1):  # if assigned boost button is pressed
                multiplier = 5

            print("Message from {}: {}, {}, {}".format(adr, x, y, b))

            '''
            Map the values of the controls into values to be used to
            create the pulses. Since the servo requires pulses ranging
            from 0.9ms to 2.1ms and duty cycle of 1 equals to 0.01ms
            pulse (as earlier commented), we'll map the values
            accordingly. Because of the way I installed the servo, it
            was turning the wrong way initially which is why I had to 
            invert it.

            Motor controlling via the ESC: 2ms pulse 
            means 100% power and 1ms pulse means 100% power
            to the reverse direction (simplified). Duty cycle
            value of 1 means 0.001ms (as earlier commented) so we'll
            have to use the range from 1000 to 2000 to reach 1ms and 
            2ms. The logic seems to be a bit flawed at the moment, as
            you'll have to use the boost button to be able to reach
            braking signal after moving forward (close to 1ms). There's
            room to improve.
            '''

            x1 = valmap(x, 0, 255, 210, 90)
            y1 = valmap(y, 0, 255, 1500 - (100 * multiplier), 1500 + (100 * multiplier))
            print("values: x{}, y{}".format(x1, y1))
            pi.set_PWM_dutycycle(MOTOR, y1)
            pi.set_PWM_dutycycle(SERVO, x1)

        except KeyboardInterrupt:
            print("exiting")
            break
        except socket.timeout:
            # if 1 second passed without receiving data, stop the car.
            print("timed out")
            pi.set_PWM_dutycycle(MOTOR, 0)  # no pulses at all
            pi.set_PWM_dutycycle(SERVO, 0)


main()