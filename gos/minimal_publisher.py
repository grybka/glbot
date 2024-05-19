import Node
import threading
import time

node=Node.Node("minimal_publisher")
node.start()

try:
    while(True):
        time.sleep(1)
        node.topic_publisher.publish("test_key", "test message")
except KeyboardInterrupt:
    print("keyboard interrupt")

node.disconnect()

