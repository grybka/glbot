import time
import logging
import sys
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug("creating node")
node=Node.Node("script","10.0.0.134")
node.start()
node.wait_until_ready()

logger.debug("moning motor a")
#node.call_service("motor_a/run_for_seconds/goal",gos.gos_encode_json_message({"speed": 50,"seconds": 1}))
#time.sleep(3)
logger.debug("moning motor a back")
#node.call_service("motor_a/run_for_seconds/goal",gos.gos_encode_json_message({"speed": -50,"seconds": 1}))
#time.sleep(3)
logger.debug("moning motor a")
node.call_service("motor_b/run_for_seconds/goal",gos.gos_encode_json_message({"speed": 50,"seconds": 0.5}))
time.sleep(2)
node.call_service("motor_b/run_for_seconds/goal",gos.gos_encode_json_message({"speed": -50,"seconds": 0.5}))
time.sleep(2)

node.disconnect()