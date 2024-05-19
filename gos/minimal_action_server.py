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
logger.setLevel(logging.DEBUG)

node=Node.Node("minimal_action_server",servername="10.0.0.134")

class MinimalActionServer(Node.SimpleActionServer):
    def __init__(self,node):
        super().__init__(node)
        self.add_action("my_action")        

    def perform_action(self,key,message):
        logging.debug("beginning calculation")
        if not isinstance(message,int):
            logger.warning("not given an integer")
            return gos.gos_encode_bool_message(False)
        goal_number=int(message)
        my_progress=[]
        a=0
        b=1
        for i in range(goal_number):
            time.sleep(1)
            c=a+b
            my_progress.append(c)
            logger.debug("publishing {}".format(c))
            node.publish(self.progress_topic,gos.gos_encode_int_message(c))
            b=a
            a=c
            if self.should_cancel:                    
                break
        return gos.gos_encode_json_message(my_progress)
        if not self.should_cancel:
            return gos.gos_encode_json_message(my_progress)



myaction=MinimalActionServer(node)
myaction.start()

try:
    while(True):
        time.sleep(1)
except KeyboardInterrupt:
    print("keyboard interrupt")

myaction.should_cancel=True
myaction.should_quit=True
myaction.join()
node.disconnect()