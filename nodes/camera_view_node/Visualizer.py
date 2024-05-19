import sys
import logging
import depthai as dai
import threading
import time
import cv2
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos
import numpy as np
import cv2
from depthai_sdk.classes.enum import ResizeMode
from depthai_sdk.oak_outputs.normalize_bb import NormalizeBoundingBox

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

nn_labels=[
            "person",
            "bicycle",
            "car",
            "motorbike",
            "aeroplane",
            "bus",
            "train",
            "truck",
            "boat",
            "traffic light",
            "fire hydrant",
            "stop sign",
            "parking meter",
            "bench",
            "bird",
            "cat",
            "dog",
            "horse",
            "sheep",
            "cow",
            "elephant",
            "bear",
            "zebra",
            "giraffe",
            "backpack",
            "umbrella",
            "handbag",
            "tie",
            "suitcase",
            "frisbee",
            "skis",
            "snowboard",
            "sports ball",
            "kite",
            "baseball bat",
            "baseball glove",
            "skateboard",
            "surfboard",
            "tennis racket",
            "bottle",
            "wine glass",
            "cup",
            "fork",
            "knife",
            "spoon",
            "bowl",
            "banana",
            "apple",
            "sandwich",
            "orange",
            "broccoli",
            "carrot",
            "hot dog",
            "pizza",
            "donut",
            "cake",
            "chair",
            "sofa",
            "pottedplant",
            "bed",
            "diningtable",
            "toilet",
            "tvmonitor",
            "laptop",
            "mouse",
            "remote",
            "keyboard",
            "cell phone",
            "microwave",
            "oven",
            "toaster",
            "sink",
            "refrigerator",
            "book",
            "clock",
            "vase",
            "scissors",
            "teddy bear",
            "hair drier",
            "toothbrush"        
        ]

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

class VisObject:
    def draw(self,frame):
        ...

class CameraWindow:
    def __init__(self,im_scale=1) -> None:
        self.objects=[]
        self.im_scale=im_scale  
        self.fps=FPSObject()         

    def draw(self,frame):
        if self.im_scale==1:
            retframe=frame
        else:
            retframe=cv2.resize(frame, (frame.shape[0]*self.im_scale,frame.shape[1]*self.im_scale) )
        self.fps.note_frame()
        cv2.putText(retframe, "FPS {:0.1f}".format(self.fps.get_fps()), (10,20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, (255,0,0))
        return retframe



class DetectionDrawer:
    def __init__(self):
        self.fill_transparency=0.1
        self.thickness = 1
        self.fill_transparency = 0.15
        self.box_roundness = 0
        self.color=(0,255,0)
        bbox_style = 0 #rectancle
        self.line_width = 4
        self.line_height = 4
        self.hide_label = False
        self.label_position=0 #top left
        self.label_padding = 10
        self.normalizer = NormalizeBoundingBox( (1,1),0)
        
    def draw(self,frame,bbox=None,label=None,id=None):
#    def draw(self,frame,detection=None,)
        #bbox = detection[0], detection[1], detection[2], detection[3]
        #print("bbox {}".format(bbox))
        #normalized_bbox = self.normalizer.normalize(frame, bbox)
        style=0
        if style==0:
            self.draw_bbox(frame, (bbox[0],bbox[1]),(bbox[2],bbox[3]),self.color,self.thickness,0,0,0)
        elif style==1: #corners
            box_w = detection[2]-detection[0]
            box_h = detection[3]-detection[1]
            line_width = int(box_w * self.line_width) // 2
            line_height = int(box_h * self.line_height) // 2
            self.draw_bbox(frame, (bbox[0],bbox[1]),(bbox[2],bbox[3]),self.color,self.thickness,0,line_width=line_width, line_height=line_height)
        elif style==2: #round rect
            box_w = detection[2]-detection[0]
            box_h = detection[3]-detection[1]
            line_width = int(box_w * self.line_width) // 2
            line_height = int(box_h * self.line_height) // 2
            self.draw_bbox(frame, (bbox[0],bbox[1]),(bbox[2],bbox[3]),self.color,self.thickness,20,0,0)



        self.draw_bbox(frame, (bbox[0],bbox[1]),(bbox[2],bbox[3]),self.color,self.thickness,0,self.line_width,self.line_height)

        #self.draw_bbox(frame, (detection[0],detection[1]),(detection[2],detection[3]),self.color,self.thickness,0,self.line_width,self.line_height)
        if label is not None:
            cv2.putText(frame, "{}".format(nn_labels[label]), (bbox[0], bbox[1]+1), cv2.FONT_HERSHEY_TRIPLEX, 0.4, self.color)
        if id is not None:
            cv2.putText(frame, "Track {}".format(id), (bbox[0], bbox[1]+12), cv2.FONT_HERSHEY_TRIPLEX, 0.4, self.color)
        #cv2.putText(frame, "x {:0.2f}\n".format(detection[5]), (detection[0], detection[1]+10), cv2.FONT_HERSHEY_TRIPLEX, 0.4, self.color)
        #cv2.putText(frame, "y {:0.2f}\n".format(detection[6]), (detection[0], detection[1]+20), cv2.FONT_HERSHEY_TRIPLEX, 0.4, self.color)
        #cv2.putText(frame, "z {:0.2f}\n".format(detection[7]), (detection[0], detection[1]+30), cv2.FONT_HERSHEY_TRIPLEX, 0.4, self.color)






    def draw_bbox(self,
                  img: np.ndarray,
                  pt1,
                  pt2,
                  color,
                  thickness: int,
                  r: int,
                  line_width: int,
                  line_height: int) -> None:
        """ #From depthai-sdk
        Draw a rounded rectangle on the image (in-place).
        Args:
            img: Image to draw on.
            pt1: Top-left corner of the rectangle.
            pt2: Bottom-right corner of the rectangle.
            color: Rectangle color.
            thickness: Rectangle line thickness.
            r: Radius of the rounded corners.
            line_width: Width of the rectangle line.
            line_height: Height of the rectangle line.
        Returns:
            None
        """
        x1, y1 = pt1
        x2, y2 = pt2

        if line_width == 0:
            line_width = np.abs(x2 - x1)
            line_width -= 2 * r if r > 0 else 0  # Adjust for rounded corners

        if line_height == 0:
            line_height = np.abs(y2 - y1)
            line_height -= 2 * r if r > 0 else 0  # Adjust for rounded corners

        # Top left
        cv2.line(img, (x1 + r, y1), (x1 + r + line_width, y1), color, thickness)
        cv2.line(img, (x1, y1 + r), (x1, y1 + r + line_height), color, thickness)
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)

        # Top right
        cv2.line(img, (x2 - r, y1), (x2 - r - line_width, y1), color, thickness)
        cv2.line(img, (x2, y1 + r), (x2, y1 + r + line_height), color, thickness)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)

        # Bottom left
        cv2.line(img, (x1 + r, y2), (x1 + r + line_width, y2), color, thickness)
        cv2.line(img, (x1, y2 - r), (x1, y2 - r - line_height), color, thickness)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)

        # Bottom right
        cv2.line(img, (x2 - r, y2), (x2 - r - line_width, y2), color, thickness)
        cv2.line(img, (x2, y2 - r), (x2, y2 - r - line_height), color, thickness)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)

        # Fill the area
        alpha = self.fill_transparency
        if alpha > 0:
            overlay = img.copy()

            thickness = -1
            bbox = (pt1[0], pt1[1], pt2[0], pt2[1])

            top_left = (bbox[0], bbox[1])
            bottom_right = (bbox[2], bbox[3])
            top_right = (bottom_right[0], top_left[1])
            bottom_left = (top_left[0], bottom_right[1])

            top_left_main_rect = (int(top_left[0] + r), int(top_left[1]))
            bottom_right_main_rect = (int(bottom_right[0] - r), int(bottom_right[1]))

            top_left_rect_left = (top_left[0], top_left[1] + r)
            bottom_right_rect_left = (bottom_left[0] + r, bottom_left[1] - r)

            top_left_rect_right = (top_right[0] - r, top_right[1] + r)
            bottom_right_rect_right = (bottom_right[0], bottom_right[1] - r)

            all_rects = [
                [top_left_main_rect, bottom_right_main_rect],
                [top_left_rect_left, bottom_right_rect_left],
                [top_left_rect_right, bottom_right_rect_right]
            ]

            [cv2.rectangle(overlay, pt1=rect[0], pt2=rect[1], color=color, thickness=thickness) for rect in all_rects]

            cv2.ellipse(overlay, (top_left[0] + r, top_left[1] + r), (r, r), 180.0, 0, 90, color, thickness)
            cv2.ellipse(overlay, (top_right[0] - r, top_right[1] + r), (r, r), 270.0, 0, 90, color, thickness)
            cv2.ellipse(overlay, (bottom_right[0] - r, bottom_right[1] - r), (r, r), 0.0, 0, 90, color, thickness)
            cv2.ellipse(overlay, (bottom_left[0] + r, bottom_left[1] - r), (r, r), 90.0, 0, 90, color, thickness)

            cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)