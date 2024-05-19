import threading
import sys
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos
import logging
import time
import numpy as np

#This takes in a track positions message from the camera
#and sends motor commands to point the camera
#
#It needs to figure out which thing it is supposed to track
#Add that as a service? start with just first thing on the list
#
#Services
#  Enable / disable tracking

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger("Node.py").setLevel(logging.WARNING)


def get_track_with_id(tracks,id):
    for track in tracks:
        if track["id"]==id:
            return track
    return None

class GazeControlNode:
    def __init__(self,name="gazecontrol",host="10.0.0.134"):
        self.node=Node.Node(name,host)
        self.node.add_service_callback("enable",self.enable_tracking_callback)
        self.node.add_listener_callback("OakD/tracks", self.track_callback)
        
        self.enabled=True
        self.target=None
        self.tracks=[]
        self.tracks_lock=threading.Lock()

        self.last_tracks=[]
        self.last_motion=None

        self.x_pos=0 #assumed position of motor x
        self.target_x_pos=0
        self.last_x_pos=None
        self.last_y_pos=None


    def enable_tracking_callback(self,key,message):
        self.enabled=True


    def track_callback(self,key,message):
        with self.tracks_lock:
            self.tracks=message["tracks"]  

    def record_track_info(self,new_tracks):
        if self.last_motion is not None:
            dat={}
            dat["old_tracks"]=self.last_tracks
            dat["new_tracks"]=new_tracks
            dat["last_x_motion"]=self.last_motion
            self.node.topic_publisher.publish("log_this", gos.gos_encode_json_message(dat))



    def loop_step(self):
        if not self.enabled:
            return None
        
        with self.tracks_lock:
            if self.last_x_pos is None:
                self.last_x_pos=self.node.call_service("motor_a/get_position")
                if self.last_x_pos is None:
                    return #skip if no response
            if self.last_y_pos is None:
                self.last_y_pos=self.node.call_service("motor_b/get_position")
                if self.last_y_pos is None:
                    return #skip if no response
            #record track info
            self.record_track_info(self.tracks)

            #find something to track
            track=get_track_with_id(self.tracks,self.target)
            if track is None:
                if len(self.tracks)==0:
                    #logger.debug("no tracks")
                    return None #no tracks
                #find a new target    
                for i in range(len(self.tracks)):
                    if self.tracks[i]['status']=='TRACKED':
                        self.target=self.tracks[0]["id"]
                        track=self.tracks[0]
                #logger.debug("tracking id {}".format(self.target))
                    
            


            #figure out error
            x_center=(track["roi"][0]+track["roi"][2])/2
            y_center=(track["roi"][1]+track["roi"][3])/2

            x_err=x_center-0.5
            y_err=y_center-0.5

            #TODO log errors and whatever other info there is

        #x_gain=-200/360
        #delta_x=x_err*x_gain
        x_gain=-1.27 #from fit
        delta_x=x_err/x_gain


        #Random motion.  This worked
        #delta_x=0.05*np.random.normal()-self.last_pos/360 #this makes it always look about towards center
        #logger.debug("turning {}".format(delta_x))
        #delta_x=np.clip(delta_x,-1,1)
        #logger.debug("clipped to {}".format(delta_x))

        #Random y motion.  Untested
        #delta_y=0.02*np.random.normal()-self.last_y_pos/360 #this makes it always look about towards center
        #logger.debug("pitching {}".format(delta_y))
        #delta_y=np.clip(delta_x,-0.25,0.25)
        #logger.debug("clipped to {}".format(delta_y))

        if abs(delta_x)>2/360:
            self.last_motion=delta_x
            self.x_pos+=delta_x
            pos=self.node.call_action("motor_a/run_for_rotations",gos.gos_encode_double_message(delta_x))
            #logger.debug("last_pos: {}, new pos: {}, difference {}".format(self.last_pos,pos,pos-self.last_pos))
            #logger.debug("Expected difference: {}".format(delta_x*360))
            self.last_pos=pos
        else:
            self.last_motion=0

        if abs(delta_y)>2/360:
            self.last_motion=delta_y
            self.y_pos+=delta_y
            pos=self.node.call_action("motor_b/run_for_rotations",gos.gos_encode_double_message(delta_y))
            #logger.debug("last_pos: {}, new pos: {}, difference {}".format(self.last_pos,pos,pos-self.last_pos))
            #logger.debug("Expected difference: {}".format(delta_x*360))
            self.last_y_pos=pos
        else:
            self.last_y_motion=0


    def old(self):
        #done with lock
        x_gain=-200
        self.target_x_pos=self.target_x_pos+x_err*x_gain
        if abs(round(self.target_x_pos)-self.x_pos)>2:
            self.x_pos=round(self.target_x_pos)
            logger.debug("Setting new position {}".format(self.x_pos))                    
            self.node.call_action("motor_a/run_to_position",gos.gos_encode_double_message(self.x_pos))
        #logger.debug("error: {} {}".format(x_err,y_err))

if __name__=='__main__':
        gaze_control=GazeControlNode()
        gaze_control.node.start()
        min_wait_time=0.1
        try:
            while(True):
                start_time=time.time()
                gaze_control.loop_step()
                wait_time=min_wait_time+time.time()-start_time
                if wait_time>0:
                    time.sleep(wait_time)

        except KeyboardInterrupt:
            print("keyboard interrupt")
        gaze_control.node.disconnect()
                





        ...

