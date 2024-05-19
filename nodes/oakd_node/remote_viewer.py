from MJPEG_client import MJPEG_client

from MJPEG_Frame import MJPEG_Frame
import time
import logging
import cv2
import threading


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

  
#logger.basicConfig(level=logging.WARNING)
test_port=23033



class FPSObject:
    def __init__(self):
        self.start_time=time.time()
        self.frames=0
        self.update_at_frame=20
        self.fps=0

    def reset(self):
        self.start_time=time.time()
        self.frames=0

    def note_frame(self):
        self.frames=self.frames+1
        if self.frames>=self.update_at_frame:
            self.fps=self.frames/(time.time()-self.start_time)
            self.reset()

    def get_fps(self):
        return self.fps


class DisplayLoop():
    def __init__(self):
        self.window_images={}
        self.open_windows=[]
        self.frame_lock=threading.Lock()

    def update_image(self,windowname,image):
        self.frame_lock.acquire()
        self.window_images[windowname]=image
        self.frame_lock.release()

    def one_loop(self):
        self.frame_lock.acquire()
        #logging.debug("camera loop with {} windows ".format(len(self.window_images)))
        for key in self.window_images:
            if key not in self.open_windows:
                cv2.namedWindow(key)
                self.open_windows.append(key)
            try:
                cv2.imshow(key, self.window_images[key])
            except:
                logger.warning("unable to show image in window {}".format(key))
        self.frame_lock.release()
        key = cv2.waitKey(30)

    def __del__(self):
        if cv2 is not None:
            cv2.destroyAllWindows()


#window_name="gratbot_view"
#cv2.namedWindow(window_name)
displayloop=DisplayLoop()

def callback(data):
    displayloop.update_image("gratbot_view",data.frame)
    #try:
    #    cv2.imshow(window_name,data.frame)
    #except:
    #    logger.waring("unable to show frame!")


client=MJPEG_client(callback=callback)
client.start_client("10.0.0.134",test_port)
print("client started")
last_send=0


try:
    while True:
        time.sleep(0.01) 
        displayloop.one_loop()
               
except KeyboardInterrupt:
    logger.error("Keyboard interrupt")
finally:
    client.quit()