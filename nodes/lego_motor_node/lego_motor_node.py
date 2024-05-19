import threading, queue
import time
import logging
import sys
import numpy as np
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos
from buildhat import Motor

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class LegoMotorNode(Node.SimpleActionServer):
    def __init__(self,name,connection,motor_letter):
        logger.debug("Connecting to motor {}".format(motor_letter))
        self.motor=Motor(motor_letter)
        self.motor.set_default_speed(50)
        logger.debug("Connected to motor")
        node=Node.Node(name)
        super().__init__(node)
        self.add_action("run_for_rotations")
        self.add_action("run_to_position")

        self.node.add_service_callback("get_position",self.get_position_callback)
        self.node.add_service_callback("run_at_speed",self.run_at_speed_callback)
        self.node.add_service_callback("stop",self.stop_callback)


        #self.node.add_action_server("rotate_degrees",self.rotate_degrees_callback,self.unsupported_callback)
        #self.node.add_action_server("run_to_position",self.run_to_position_callback,self.unsupported_callback)
        #self.node.add_action_server("run_for_rotations",self.action_callback,self.unsupported_callback)
        #self.node.add_action_server("run_for_degrees",self.action_callback,self.unsupported_callback)

        #self.node.add_action_server("run_for_seconds",self.run_for_seconds_callback,self.unsupported_callback)
        self.node.add_service_callback("set_speed",self.set_speed_callback)
        #-- thread stuff
        #maxsize=1
        #self.acting_lock=threading.Lock()
        #self.action_request=None #it's a (key,message) pair
        #self.should_quit=False
        #self.thread = threading.Thread(target=self._thread_loop)
        #self.thread.daemon = True

        self.max_position=180
        self.min_position=-180


    #def start(self):
    #    self._thread.start()

    def set_speed_callback(self,key,message):
        logger.debug("setting speed to {}".format(message))
        self.motor.set_default_speed(message)
        return gos.gos_encode_bool_message(True)

    def get_position_callback(self,key,message):
        pos=self.motor.get_aposition()
        return gos.gos_encode_double_message(float(pos))
    
    def run_at_speed_callback(self,key,message):
        the_speed=float(message)
        logger.debug("setting speed to {}".format(the_speed))
        self.motor.start(speed=the_speed)
        return gos.gos_encode_bool_message(True)


    def stop_callback(self,key,message):
        logger.debug("stopping")
        self.motor.stop()
        return gos.gos_encode_bool_message(True)



 #   def action_callback(self,key,message):
 #       logger.debug("action callback with {}".format(key))
 #       try:
 #           self.action_queue.put( (key,message) )
 #       except queue.Full:
 #           return gos.gos_encode_bool_message(False)
 #       return gos.gos_encode_bool_message(True)

    def perform_action(self,key,message):
        logger.debug("received message {}".format(message))
        if key.endswith("run_for_rotations/goal"):
            logger.debug("runnig for rotations {}".format(message))
            rotations=float(message)
            self.motor.run_for_rotations(rotations,blocking=True)
            pos=self.motor.get_aposition()
            return gos.gos_encode_double_message(float(pos))
            
        if key.endswith("run_to_position/goal"):
            logger.debug("running to position {}".format(message))
            if float(message)>self.max_position or float(message)<self.min_position:
                logger.debug("position {} out of bounds {} to {}".format(float(message),self.min_position,self.max_position))
            
            position=np.clip(float(message),self.min_position,self.max_position)
            self.motor.run_to_position(position,blocking=True)
            return gos.gos_encode_bool_message(True)
        logger.warning("Unhandled key {}".format(key))    

if __name__=="__main__":
    motor_a=LegoMotorNode("motor_a",None,"A")
    motor_a.min_position=-180
    motor_a.max_position=180
    motor_b=LegoMotorNode("motor_b",None,"B")
    motor_a.start()
    motor_b.start()
    try:
        while(True):
            time.sleep(1)
    except KeyboardInterrupt:
        print("keyboard interrupt")
    motor_a.node.disconnect()
    motor_b.node.disconnect()