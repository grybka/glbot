import numpy as np
import cv2

class MJPEG_Frame:
    def __init__(self,frame):
        self.frame=frame

    def serialize(self):
        #returns length,data(bytes)
        #image=np.frombuffer(nbytes,dtype=np.uint8)
        _,frame=cv2.imencode('.jpg',self.frame)
        return len(frame),frame.tobytes()
    
    @staticmethod
    def unserialize(data):
        ray=np.frombuffer(data,dtype=np.uint8)
        return MJPEG_Frame(cv2.imdecode(ray,cv2.IMREAD_COLOR))
