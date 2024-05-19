import Node
import threading
import time
import logging
import uuid
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
node=Node.Node("minimual_service_client")
node.start()


try:
    while(True):
        time.sleep(1)
        print("calling service")
        result=node.call_service("my_service","")
        print("called service with result {}".format(result))
        
        #node.topic_publisher.publish("test_key", "test message")
except KeyboardInterrupt:
    print("keyboard interrupt")

node.disconnect()