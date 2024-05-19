import threading, queue
import time
import logging
import sys
sys.path.append('../gos')
import Node
import gos_wire_protocol as gos

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logging.getLogger("Node.py").setLevel(logging.WARNING)

class CollectXTrack:
    def __init__(self,name="collect_xtrack_data",host="10.0.0.134"):
        ...
        self.node=Node.Node(name,host)
        self.node.add_service_callback("enable",self.enable_tracking_callback)
        self.node.add_listener_callback("OakD/tracks", self.track_callback)


    def loop_step(self):
        if not self.enabled:
            return None
        
        with self.tracks_lock:
            x_center=(track["roi"][0]+track["roi"][2])/2
            y_center=(track["roi"][1]+track["roi"][3])/2

        self.node.call_action("motor_a/run_for_rotations",gos.gos_encode_double_message(delta_x))


    def track_callback(self,key,message):
        with self.tracks_lock:
            self.tracks=message["tracks"]  



def collect_epoch():
    #Set to zero position
    letter="a"
    node.call_action("motor_"+letter+"/run_to_position",gos.gos_encode_double_message(0))
    #wait until tracks found
    #move a random amount for a while
    #loop back