import sys
import logging
import depthai as dai
import threading
import time
sys.path.append('../../gos')
import Node
import gos_wire_protocol as gos
from depthai_sdk import OakCamera
import cv2
from depthai_sdk.classes.enum import ResizeMode
from depthai_sdk.oak_outputs.normalize_bb import NormalizeBoundingBox
from MJPEG_server import MJPEG_server
from MJPEG_Frame import MJPEG_Frame


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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

class OakDNode:
    def __init__(self,name="OakD"):
        #self.oak_comm_thread=None
        #self.should_quit=False
        self.name=name
        self.node=Node.Node(name,"10.0.0.134") 
        self.camera_topic=name+"/camera"      
        self.imu_topic=name+"/imu"
        self.tracker_topic=name+"/tracks"
        self.fps=FPSObject()
        #self.nn_name="yolov6"
        self.nn_name="yolov6tracking"

        #self.nn_name='mobilenet'
        #self.nn_name="yolov8"
        self.normalizer = NormalizeBoundingBox( (640,352),ResizeMode.LETTERBOX)
        #self.mjpeg_server=MJPEG_server()
        #self.mjpeg_server.start_server(port=23033)

        #self.normalizer = NormalizeBoundingBox( (352,640),ResizeMode.LETTERBOX)

        #self.normalizer = NormalizeBoundingBox( (352,640),ResizeMode.CROP)

        #self.normalizer = NormalizeBoundingBox( (640,352),ResizeMode.STRETCH)



    def init_oakd(self):
        oak=OakCamera()
        logger.debug("create color camera")
        
        color = oak.create_camera('color',fps=10)
        
        if self.nn_name=="yolov6":
            logger.debug("create yolo v6 spatial nn")
            nn = oak.create_nn('yolov6nr3_coco_640x352', color, spatial=True)
            nn.config_nn(resize_mode='letterbox')
            nn.config_spatial(
                bb_scale_factor=0.5, # Scaling bounding box before averaging the depth in that ROI
                lower_threshold=10, # Discard depth points below 10cm
                upper_threshold=10000, # Discard depth pints above 10m
                # Average depth points before calculating X and Y spatial coordinates:
                calc_algo=dai.SpatialLocationCalculatorAlgorithm.AVERAGE
            )
            oak.callback([nn.out.passthrough],self.nn_callback)

        elif self.nn_name=="yolov6tracking":
            logger.debug("create yolo v6 spatial nn with tracker")
            nn = oak.create_nn('yolov6nr3_coco_640x352', color, spatial=True,tracker=True)
            nn.config_nn(resize_mode='letterbox')
            nn.config_spatial(
                bb_scale_factor=0.5, # Scaling bounding box before averaging the depth in that ROI
                lower_threshold=10, # Discard depth points below 10cm
                upper_threshold=10000, # Discard depth pints above 10m
                # Average depth points before calculating X and Y spatial coordinates:
                calc_algo=dai.SpatialLocationCalculatorAlgorithm.AVERAGE
            )
            nn.config_tracker(
                #tracker_type=dai.TrackerType.ZERO_TERM_IMAGELESS,
                #tracker_type=dai.TrackerType.SHORT_TERM_KCF,
                tracker_type=dai.TrackerType.ZERO_TERM_COLOR_HISTOGRAM,
                track_labels=[0], # Track only 1st object from the object map. If unspecified, track all object types
                # track_labels=['person'] # Track only people (for coco datasets, person is 1st object in the map)
                assignment_policy=dai.TrackerIdAssignmentPolicy.SMALLEST_ID,
                max_obj=10, # Max objects to track, which can improve performance
                threshold=0.1 # Tracker threshold
            )
            oak.callback([nn.out.passthrough],self.image_callback)
            oak.callback([nn.out.tracker],self.tracker_callback)

        elif self.nn_name=="mobilenet":
            logger.debug("create mobilenet spatial nn")
            nn = oak.create_nn('mobilenet-ssd', color, spatial=True)
        elif self.nn_name=="yolov8":
            logger.debug("create yolo v8 spatial nn")
            nn = oak.create_nn('yolov8n_coco_640x352', color, spatial=True)        
            nn.config_spatial(
                bb_scale_factor=0.5, # Scaling bounding box before averaging the depth in that ROI
                lower_threshold=10, # Discard depth points below 10cm
                upper_threshold=10000, # Discard depth pints above 10m
                # Average depth points before calculating X and Y spatial coordinates:
                calc_algo=dai.SpatialLocationCalculatorAlgorithm.AVERAGE
            )



        #IMU
        #logger.debug("Creating IMU Object")
        #imu = oak.create_imu()
        #imu.config_imu(report_rate=100, batch_report_threshold=5,sensors=[dai.IMUSensor.ROTATION_VECTOR,dai.IMUSensor.ACCELEROMETER_RAW])
        #imu.config_imu(report_rate=100, batch_report_threshold=5)        
        #oak.callback(imu.out,self.imu_callback)

        #oak.callback([color],self.camera_callback) 
        #oak.callback(nn.out.main,self.nn_callback)       
        #oak.callback([nn.out.passthrough],self.camera_callback)
        #oak.callback([nn.out.main],self.nn_callback)
        
        #oak.visualize([nn, nn.out.passthrough], fps=True)
        #logger.debug("create color camera")
        self.oak=oak
        logger.debug("calling start")
        oak.start(blocking=False)
        #oak.start(blocking=True)

    def __del__(self):
        logger.debug("Closing OAK Device")
        if self.oak._oak.device is not None:
            self.oak._oak.device.close()
        self.mjpeg_server.quit()


    def camera_callback(self,packet):
        #logger.debug("got packet of type {}".format(type(packet)))
        sequenceNum=packet.msg.getSequenceNum()
        image_info={"sequence_num": sequenceNum}
        self.node.publish(self.camera_topic,gos.gos_encode_annotated_image(packet.frame,image_info))  

    def imu_callback(self,packet):
        logger.debug("packet data type is {}".format(type(packet.data)))
        last_packet=packet.data[-1]
        #imuPacket.acceleroMeter
        message_array=[last_packet.data.acceleroMeter.x,last_packet.data.acceleroMeter.y,last_packet.data.acceleroMeter.z]
        self.node.publish(self,imu_topic,gos.gos_encode_double_numpy_array(self.imu_topic,np.array(message_array)))

    def image_callback(self,packet):
        self.fps.note_frame()
        if self.fps.frames==0:
            logger.debug("FPS: {} at ({})".format(self.fps.get_fps(),packet.frame.shape))
            logger.debug("waiting messages: {}".format(self.node.topic_publisher.message_queue.qsize()))
        sequenceNum=packet.msg.getSequenceNum()
        image_info={"sequence_num": sequenceNum}
        _,compressed_frame=cv2.imencode('.jpg',packet.frame)
        self.node.publish(self.camera_topic,gos.gos_encode_annotated_image(compressed_frame,image_info))  



    def tracker_callback(self,packet):
        tracklets=packet.daiTracklets.tracklets 
        #detections=packet.detections
        detections=[]
        sequenceNum=packet.msg.getSequenceNum()
        image_info={"sequence_num": sequenceNum}
        tracklet_info=[]

        for t in tracklets:
            id=t.id
            status=t.status.name
            roi=t.roi
            spatial=t.spatialCoordinates
            bbox=roi.topLeft().x,roi.topLeft().y,roi.bottomRight().x,roi.bottomRight().y
            #bbox=roiData.roi.topLeft().x,roiData.roi.topLeft().y,roiData.roi.bottomRight().x,roiData.roi.bottomRight().y
            nbbox = self.normalizer.normalize(packet.frame, bbox)
            #nbbox=int(nbbox[0])
            #serialize
            detser={"id": id,"label": t.label,"status": status, "spatial": [spatial.x,spatial.y,spatial.z],"roi": [bbox[0],bbox[1],bbox[2],bbox[3]]}
            tracklet_info.append(detser)
            detections.append( [int(nbbox[0]),int(nbbox[1]),int(nbbox[2]),int(nbbox[3]),id,spatial.x,spatial.y,spatial.z]     )       
            def printvar(nm,x):
                print("{} ({}): {}".format(nm,type(x),x))
            #printvar("id",id)
            #printvar("label",t.label)
            #printvar("status",status)
            #printvar("spatial",spatial)   
        #image_info["detections"]=detections
        image_info["tracks"]=tracklet_info
        self.node.publish(self.tracker_topic,gos.gos_encode_json_message(image_info))
 
        #rframe=cv2.resize(packet.frame,(640,352))
        #_,compressed_frame=cv2.imencode('.jpg',rframe)
        #self.node.publish(self.camera_topic,gos.gos_encode_annotated_image(compressed_frame,image_info))  

    def nn_callback(self,packet):
        detections=list(packet.img_detections.detections)
        self.fps.note_frame()
        if self.fps.frames==0:
            logger.debug("FPS: {} at ({})".format(self.fps.get_fps(),packet.frame.shape))
            logger.debug("{} detections".format(len(detections)))            

        sequenceNum=packet.msg.getSequenceNum()
        image_info={"sequence_num": sequenceNum}
        detections=[]
        for detection in packet.img_detections.detections:
            #Detection layout
            #[bbox_x1,bbox_x2,bbox_y1,bbox_y2,label]
            roiData = detection.boundingBoxMapping
            roi = roiData.roi
            bbox=roiData.roi.topLeft().x,roiData.roi.topLeft().y,roiData.roi.bottomRight().x,roiData.roi.bottomRight().y
            nbbox = self.normalizer.normalize(packet.frame, bbox)

            spatial=detection.spatialCoordinates

            #roi = roi.denormalize(packet.frame.shape[1], packet.frame.shape[0])
            
            #topLeft = roi.topLeft()
            #bottomRight = roi.bottomRight()
            #xmin = int(topLeft.x)
            #ymin = int(topLeft.y)
            #xmax = int(bottomRight.x)
            #ymax = int(bottomRight.y)
            #detections.append( [xmin,ymin,xmax,ymax,detection.label]     ) 
            detections.append( [int(nbbox[0]),int(nbbox[1]),int(nbbox[2]),int(nbbox[3]),detection.label,spatial.x,spatial.y,spatial.z]     )       
      

        #my_frame=MJPEG_Frame(packet.frame)
        #while not self.mjpeg_server.output_queue.empty():
            #self.mjpeg_server.output_queue.get_nowait() #Drop frame
        #self.mjpeg_server.output_queue.put_nowait(my_frame)

        image_info["detections"]=detections
        #dim=( int(packet.frame.shape[1]/2),int(packet.frame.shape[0]/2))
        #resized_frame=cv2.resize(packet.frame,dim)
        _,compressed_frame=cv2.imencode('.jpg',packet.frame)
        #logger.debug("Before: {} After: {}".format(packet.frame.size,compressed_frame.size))        
        self.node.publish(self.camera_topic,gos.gos_encode_annotated_image(compressed_frame,image_info))  
        
        
        
        
                    

if __name__=="__main__":
    myoakd=OakDNode()
    myoakd.node.start()
    myoakd.node.wait_until_ready()
    myoakd.init_oakd()
    logger.debug("beginnig polling loop")
    try:
        while(True):
            if myoakd.oak.poll() == None:
                logger.error("Oak D disconnected")
            time.sleep(0.001)
    except KeyboardInterrupt:
        logger.warning("keyboard interrupt")
    myoakd.node.disconnect()   
