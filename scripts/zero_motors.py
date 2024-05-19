import threading, queue
import time
import logging
import sys
sys.path.append('../gos')
import Node
import gos_wire_protocol as gos

node=Node.Node("zero_motors_script","10.0.0.134")
node.start()

input("Disconnect gears and press enter")

node.wait_until_ready()

def zero_motor(letter):
    print("Zeroing Motor {}".format(letter))
    print("Initial Position {}".format(node.call_service("motor_"+letter+"/get_position")))
    print("Result: {}".format(node.call_action("motor_"+letter+"/run_to_position",gos.gos_encode_double_message(0))))    
    print("Final Position {}".format(node.call_service("motor_"+letter+"/get_position")))


zero_motor("a")
zero_motor("b")

node.disconnect()