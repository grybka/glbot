import time
import json
import sys
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos
import logging
import time

#listens to the "log_this" messages and logs them

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger("Node.py").setLevel(logging.WARNING)


class MessageLoggerNode:
    def __init__(self,name="messagelogger",host="10.0.0.134",logfile_name="logfile.log"):
        self.node=Node.Node(name,host)
        self.logfile_name=logfile_name
        self.node.add_listener_callback("log_this", self.log_this_callback)
        self.logfile=open(self.logfile_name,"w")

    def close(self):
        self.logfile.close()

    def log_this_callback(self,key,message):
        try:
            self.logfile.write(json.dumps(message)+"\n")
        except:
            print("Error writing message {}".format(message))

if __name__=='__main__':
        message_logger=MessageLoggerNode()
        message_logger.node.start()
        try:
            while(True):
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("keyboard interrupt")
        finally:
            message_logger.close()
            message_logger.node.disconnect()
                

