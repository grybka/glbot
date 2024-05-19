import time
import sys
import json
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos
import logging
import time


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger("Node.py").setLevel(logging.WARNING)

node=Node.Node("logemitted","localhost")
node.start()


try:
    while(True):
        time.sleep(1.0)
        node.publish("log_this",gos.gos_encode_json_message(json.loads('{ "from":"me","to":"you"}')))
except KeyboardInterrupt:
    print("keyboard interrupt")
finally:
    node.disconnect()