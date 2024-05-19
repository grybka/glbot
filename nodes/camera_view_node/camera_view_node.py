import sys
import logging
import depthai as dai
import threading
import time
import cv2
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos
import cv2
import numpy as np
from Visualizer import DisplayLoop,CameraWindow,DetectionDrawer,FPSObject

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CameraDisplayNode:
    def __init__(self,display,host):
        self.node=Node.Node("CameraDisplay",host)
        self.display=display
        self.node.add_listener_callback("OakD/camera", self.on_camera_frame)
        self.node.add_listener_callback("OakD/tracks", self.on_tracker_frame)

        self.camera_window=CameraWindow()
        self.detection_drawer=DetectionDrawer()
        self.fps=FPSObject()

        time_counter=0
        n_counter=0

        self.last_tracker_packet=None

    def on_camera_frame(self,routing_key,message):

        start_time=time.time()
        base_frame=cv2.imdecode(message[0],cv2.IMREAD_COLOR)
        metadata=message[1]
        frame=self.camera_window.draw(base_frame)  
        #frame=np.zeros([480,630,3])
        if self.last_tracker_packet is not None:   
            for track in self.last_tracker_packet["tracks"]:
                #print("roi {}".format(track["roi"]))
                bbox=[int(track["roi"][0]*640),int(track["roi"][1]*382),int(track["roi"][2]*640),int(track["roi"][3]*382)]
                self.detection_drawer.draw(frame,bbox=bbox,id=track["id"],label=track["label"])
                ...
        elif "detections" in metadata:
            for detection in metadata["detections"]:
                ...
                self.detection_drawer.draw(frame,detection)      
        #for t in metadata["tracks"]:
        #    detection=[t["roi"][0],t["roi"][1],t["roi"][2],t["roi"][3] ]

        self.fps.note_frame()
        if self.fps.frames==0:
            logger.debug("Received FPS: {} at {}".format(self.fps.get_fps(),frame.shape))
            #logger.debug("{} detections".format(len(metadata["detections"])))

        self.display.update_image("camera",frame)      
        #print("time spent: {}".format(time.time()-start_time))

    def on_tracker_frame(self,routing_key,message):
        self.last_tracker_packet=message



        
#    def post_image(self,routing_key,message):
#        frame=message[0]
#        logger.debug("posting image")
#        logger.debug("{}".format(message[1]["detections"]))
#        self.display.update_image("camera",frame)

if __name__=='__main__':
    display_loop=DisplayLoop()
    #cdn=CameraDisplayNode(display_loop,"10.0.0.134")
    cdn=CameraDisplayNode(display_loop,"10.0.0.10")
    cdn.node.start()
    try:
        while True:
            time.sleep(0.001)
            display_loop.one_loop()
    except KeyboardInterrupt:
        logging.warning("Keyboard Exception Program Ended")
    finally:
        cdn.node.disconnect()
