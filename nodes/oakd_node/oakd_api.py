import depthai as dai
import logging
import time
import numpy as np
import os
from pathlib import Path
import blobconverter

logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class OakDManipLetterbox():
    def __init__(self,pipeline,new_size,image_in):
        #create a manipulation that resizes the camera preview
        #camRgb is a ColorCamera object
        #new_size is an array [new_x,new_y]
        #the presumption is that the aspect ratio can be squeezed
        manip = pipeline.create(dai.node.ImageManip)
        manip.setMaxOutputFrameSize(new_size[0]*new_size[1]*3) # 300x300x3
        manip.initialConfig.setResizeThumbnail(new_size[0], new_size[1])
        manip.initialConfig.setFrameType(dai.ImgFrame.Type.RGB888p)
        image_in.link(manip.inputImage)
        self.manip=manip
    #TODO this doesn't necessarily need a tryget, but you could imagine one

class OakDDepth():
    #create the depth cameras
    #create an output stream if given one
    def __init__(self,pipeline,streamname=None):
        #depth camera
        self.streamname=streamname
        logger.info("Creating Stereo Camera in pipeline")

        monoLeft = pipeline.createMonoCamera()
        monoRight = pipeline.createMonoCamera()
        monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
        monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)
        stereo = pipeline.createStereoDepth()
        stereo.setConfidenceThreshold(255)
        monoLeft.out.link(stereo.left)
        monoRight.out.link(stereo.right)
        if streamname is not None:
            depthout=pipeline.createXLinkOut()
            depthout.setStreamName(streamname)
            stereo.depth.link(depthout.input)
        self.stereo=stereo

    def build_queues(self,device):
        if self.streamname is not None:
            self.depthQueue = device.getOutputQueue(name=self.streamname, maxSize=4,blocking=False)

    def tryget(self,broker):
        #get depth from the depth queu
        #return the depth image if possible or none
        if self.streamname is not None:
            inDepth = self.depthQueue.tryGet()
            if inDepth is not None:
                frame=inDepth.getFrame()
                frame_message={"timestamp": time.time()}
                image_timestamp=inDepth.getTimestamp().total_seconds()
                frame_message["image_timestamp"]=image_timestamp
                frame_message["depth_image"]=cv2.resize(frame,(160,100),cv2.INTER_NEAREST )
                #frame_message["depth_image"]=frame
                frame_message["keys"]=["depth"]
                #broker.publish(frame_message,frame_message["keys"])


#Make a MobilenetV2 spatial detection network
#name,shaves is the name of the blob
#camera is the source of images
#stereo is the source of stereo information
#streamname is the name of the output stream for detections
class OakDMobileNetDetections():
    def __init__(self,pipeline,model_name,shaves,camera,stereo,streamname,model_labels):
        self.streamname=streamname
        logger.info("Creating MobilenetV2 Detections: {}".format(self.streamname))
        self.model_labels=model_labels
        spatialDetectionNetwork = pipeline.createMobileNetSpatialDetectionNetwork()
        spatialDetectionNetwork.setBlobPath(str(blobconverter.from_zoo(name=model_name, shaves=shaves)))
        spatialDetectionNetwork.setConfidenceThreshold(0.5)
        spatialDetectionNetwork.input.setBlocking(False)
        spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
        spatialDetectionNetwork.setDepthLowerThreshold(100)
        spatialDetectionNetwork.setDepthUpperThreshold(5000)
        camera.link(spatialDetectionNetwork.input)
        stereo.depth.link(spatialDetectionNetwork.inputDepth)
        if self.streamname is not None:
            xoutNN = pipeline.createXLinkOut()
            xoutNN.setStreamName(streamname)
            spatialDetectionNetwork.out.link(xoutNN.input)
        self.spatialDetectionNetwork=spatialDetectionNetwork

    def build_queues(self,device):
        if self.streamname is not None:
            self.detectionNNQueue = device.getOutputQueue(name=self.streamname, maxSize=4, blocking=False)

    def tryget(self,broker):
        if self.streamname is None:
            return #no detections to get
        inDet = self.detectionNNQueue.tryGet()
        if inDet is not None:
            device_timestamp=inDet.getTimestamp().total_seconds()
            detection_message=[]
            for detection in inDet.detections:
                det_item={}
                bbox_array=[detection.xmin,detection.xmax,detection.ymin,detection.ymax]
                det_item["bbox_array"]=bbox_array
                det_item["spatial_array"]=[detection.spatialCoordinates.x,detection.spatialCoordinates.y,detection.spatialCoordinates.z]
                det_item["label"] = self.model_labels[detection.label]
                det_item["confidence"] = detection.confidence
                detection_message.append(det_item)
            #Send a detections message even if its empty
            frame_message={"timestamp": time.time(),"image_timestamp": device_timestamp}
            frame_message["detection_name"]=self.streamname
            frame_message["detections"]=detection_message
            #broker.publish(frame_message,["detections",self.streamname])