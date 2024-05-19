import Node
import threading
import time
import logging
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
#logger=logging.getLogger(__name__)

node=Node.Node()

def print_message(routing_key, body):
    print("got message {} on routing key {}".format(body,routing_key))

routing_key="test_key"
node.add_listener_callback(routing_key, print_message)

node.start()
try:
    while(True):
        time.sleep(1)
except KeyboardInterrupt:
    print("keyboard interrupt")

node.disconnect()