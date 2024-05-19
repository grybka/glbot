import Node
import threading
import time
import logging
import dropline_wire_protocol as dwp


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)

node=Node.Node("minimal_service_client")

def print_message(routing_key, body):
    print("got message {} on routing key {}".format(body,routing_key))

node.add_listener_callback("minimal_action_server/my_action/progress", print_message)
node.add_listener_callback("minimal_action_server/my_action/result", print_message)
node.start()

try:
    while(True):
        
        print("calling action")
        result=node.call_service("minimal_action_server/my_action/goal",dwp.dwp_encode_int_message(8))
        print("called action with result {}".format(result))

        time.sleep(10)
except KeyboardInterrupt:
    print("keyboard interrupt")

node.call_service("minimal_action_server/my_action/cancel",dwp.dwp_encode_bool_message(False))
node.disconnect()
