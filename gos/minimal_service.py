import Node
import threading
import time
import logging
import random
import gos_wire_protocol as gos

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)

node=Node.Node("minimal_service")

def respond(service_key,body):
    logger.debug("Received {}, responding".format(body))
    return gos.gos_encode_string_message(random.choice(["foo","bar","blarg"]))

node.add_service_callback("my_service",respond)

node.start()
try:
    while(True):
        time.sleep(1)
except KeyboardInterrupt:
    print("keyboard interrupt")

node.disconnect()