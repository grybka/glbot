import pika
import functools
import threading,queue
import logging
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
import uuid
import gos_wire_protocol as gos
logging.getLogger("pika").setLevel(logging.WARNING)


#How do I use AMQP-
#  a topic exchange for published data
#   -each Node makes a queue for this, filtering on topics

#How do I use pika
# one thread with its own pika connection handles messages showing up to my topics queue
# one thread with its own pika connection handles messages that need to be published

TOPIC_EXCHANGE_NAME="topic_exchange"
SERVICE_RESPONSE_TIMEOUT=2.0 #in seconds

class TopicListenerThread:
    def __init__(self,connection_parameters=None):        
        self.connection_parameters=connection_parameters
        self.should_quit = False
        self.thread = None
        self.thread = threading.Thread(target=self._thread_loop)
        self.check_quit_delay=1
        #self.thread.daemon = True
        self.topics="test"
        self.callbacks=dict()
        self.service_callbacks=dict()
        self.thread_ready=threading.Event()

    def start_thread(self):
        if self.thread is not None:
            self.thread.start()

    def join(self):
        return self.thread.join()

    def _thread_loop(self):
        while not self.should_quit:
            try:
                logger.debug("starting topic listener thread")
                #Connect
                self.connection=None
                #self.connection=pika.BlockingConnection()
                self.connection=pika.BlockingConnection(parameters=self.connection_parameters)
                self.channel=self.connection.channel()
                #Establish Queue
                self.channel.exchange_declare(exchange=TOPIC_EXCHANGE_NAME,exchange_type='topic')
                result=self.channel.queue_declare('',auto_delete=True,exclusive=True)
                self.my_queue=result.method.queue
                #bind my queue to each thing I listen for
                for k,v in self.callbacks.items():
                    logger.debug("Binding {}".format(k))
                    self.channel.queue_bind(exchange=TOPIC_EXCHANGE_NAME,queue=result.method.queue,routing_key=k)
                for k,v in self.service_callbacks.items():
                    logger.debug("Binding {}".format(k))
                    self.channel.queue_bind(exchange=TOPIC_EXCHANGE_NAME,queue=result.method.queue,routing_key=k)
                self.connection.call_later(self.check_quit_delay,self.check_for_quit)
                self.channel.basic_consume(queue=result.method.queue, on_message_callback=self.message_callback)
                self.thread_ready.set()
                self.channel.start_consuming()
            except pika.exceptions.ConnectionClosedByBroker:
                logger.warning("Listener Connection closed by broker.  Attempting reconnection")
                continue
            except pika.exceptions.AMQPConnectionError:
                logger.warning("Listener Connection error of some sort.  Attempting reconnection")
                continue
        self.channel.stop_consuming()
        self.connection.close()
        logger.debug("ending topic listener thread")

    def add_listener_callback(self, routing_key, callback):
        #callback muth have arguments (routing_key,body)
        self.callbacks[routing_key]=callback  

    def dynamic_add_listener_callback(self, routing_key, callback):
        #callback muth have arguments (routing_key,body)
        self.callbacks[routing_key]=callback  
        self.connection.add_callback_threadsafe(
            functools.partial(self.channel.queue_bind,exchange=TOPIC_EXCHANGE_NAME,queue=self.my_queue,routing_key=routing_key))

    def dynamic_remove_listener_callback(self, routing_key):
        self.callbacks.pop(routing_key)

    def add_service_callback(self, routing_key, callback):
        #callback muth have arguments (routing_key,body) and return
        self.service_callbacks[routing_key]=callback
        return routing_key

    def message_callback(self,channel,method, properties, body):
        routing_key=method.routing_key
        #logger.debug("message callback with routing key {}".format(method.routing_key))
        channel.basic_ack(delivery_tag=method.delivery_tag)
        if routing_key in self.callbacks:
            self.callbacks[routing_key](method.routing_key,gos.gos_decode(body))
        if routing_key in self.service_callbacks:            
            response=self.service_callbacks[routing_key](method.routing_key,gos.gos_decode(body))
            self.channel.basic_publish(exchange='',
                     routing_key=properties.reply_to,
                     properties=pika.BasicProperties(correlation_id = properties.correlation_id),
                     body=response)


    
    def check_for_quit(self):
        if self.should_quit is True:
            self.channel.stop_consuming()
        else:
            self.connection.call_later(self.check_quit_delay,self.check_for_quit)

class TopicPublisherThread:
    def __init__(self,connection_parameters=None):
        self.connection_parameters=connection_parameters
        self.should_quit = False
        self.thread = None
        self.thread = threading.Thread(target=self._thread_loop)
        #self.thread.daemon = True
        maxsize=10
        self.message_queue=queue.Queue(maxsize=maxsize) #Not AMQP!
        self.topics_published=set()

        #temperary variable holding  response to service requests
        self.service_response=None
        self.thread_ready=threading.Event()


    def publish(self,routing_key,message):
        self.topics_published.add(routing_key)
        try:
            self.message_queue.put( (routing_key,message,None,None),timeout=0.1 )
        except queue.Full:
            logger.warning("Publish queue full, discarding")

    def start_thread(self):
        if self.thread is not None:
            self.thread.start()

    def join(self):
        return self.thread.join()
    
    def send_service_request(self,service_routing_key,request):
        if request==None:
            request=gos.gos_encode_bool_message(True)
        event=threading.Event()
        response_array=[None]        
        self.message_queue.put( (service_routing_key,request,event,response_array) )
        if event.wait(timeout=SERVICE_RESPONSE_TIMEOUT+1):
            return response_array[0]
        else:
            logger.warning("No response to service request")
            return None
    
    def _send_service_request(self,service_routing_key,request,event,response_array):
        #send a service request and wait for response
        #this must be called within the context of the thread loop, not outside

        self.corr_id = str(uuid.uuid4())
        #publish the message
        self.channel.basic_publish(exchange=TOPIC_EXCHANGE_NAME,routing_key=service_routing_key,properties=pika.BasicProperties(reply_to = self.service_response_queue,correlation_id=self.corr_id),body=request)
        #consume the response
        response=None
        for method, properties, body in self.channel.consume(self.service_response_queue,inactivity_timeout=SERVICE_RESPONSE_TIMEOUT,auto_ack=True):
            if method==None:
                logger.warning("ERROR TIMEOUT IN SEND SERVICE REQUEST")
                break
            if properties.correlation_id!=self.corr_id:
                logger.warning("ERROR CORRELATION_ID MISMATCH IN SEND SERVICE REQUEST")
            else:
                #self.channel.basic_ack(delivery_tag=method.delivery_tag)
                response_array[0]=gos.gos_decode(body)
                break
        event.set() #tell the asking thread to wake up and deal with it
        self.channel.cancel()

    def _thread_loop(self):
        logger.debug("starting topic publisher thread")
        #Connect
        self.connection=None
        self.connection=pika.BlockingConnection(self.connection_parameters)
        self.channel=self.connection.channel()
        #Establish Exchange
        self.channel.exchange_declare(exchange=TOPIC_EXCHANGE_NAME,exchange_type='topic') 
        #Establish a Queue for service requests
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.service_response_queue = result.method.queue

        self.thread_ready.set()
        while not self.should_quit:
            #TODO a select statement might be better
            try:
                message=self.message_queue.get(timeout=0.1)
                if message[2] is None:
                    #logger.debug("publishing message on {}".format(message[0]))
                    self.channel.basic_publish(exchange=TOPIC_EXCHANGE_NAME, routing_key=message[0], body=message[1])
                else:
                    logger.debug("requesting service {}".format(message[0]))
                    self._send_service_request(message[0],message[1],message[2],message[3])
                
            except queue.Empty:
                pass
        self.connection.close()
        logger.debug("ending topic publisher thread")

NODENAME_QUERY_ROUTING_KEY="NODENAME_QUERY"
NODENAME_ROUTING_KEY="NODENAME"
NODEINFO_QUERY_ROUTING_KEY="NODEINFO"

SERVICE_QUERY_ROUTING_KEY="SERVICE_QUERY"
SERVICE_ROUTING_KEY="SERVICE"

class Node:
    def __init__(self,name="Blank Node",servername='localhost',credentials=('guest','guest')):
        self.node_name=name        
        credentials = pika.PlainCredentials('gos_user', '85259')
        #credentials = pika.PlainCredentials(credentials[0],credentials[1]) 


        self.connection_parameters=pika.ConnectionParameters(host=servername,credentials=credentials)

        self.topic_listener=TopicListenerThread(self.connection_parameters)
        self.topic_publisher=TopicPublisherThread(self.connection_parameters)
        #all nodes should have this debug info
        self.add_listener_callback(NODENAME_QUERY_ROUTING_KEY, self.respond_to_node_name_request)
        self.add_listener_callback(SERVICE_QUERY_ROUTING_KEY, self.respond_to_service_name_request)
        self.add_service_callback(NODEINFO_QUERY_ROUTING_KEY,self.respond_to_node_info_request)
        self.action_list=[]


    def wait_until_ready(self):
        self.topic_listener.thread_ready.wait(timeout=5)
        self.topic_publisher.thread_ready.wait(timeout=5)
        return True

    def start(self):
        self.topic_listener.start_thread()
        self.topic_publisher.start_thread()

    def disconnect(self):
        self.topic_listener.should_quit=True
        self.topic_publisher.should_quit=True
        logger.debug("Joining topic listener")
        self.topic_listener.join()
        logger.debug("Joining topic publisher")
        self.topic_publisher.join()

    def add_listener_callback(self, routing_key, callback):
        self.topic_listener.add_listener_callback(routing_key, callback)

    def publish(self,routing_key,message):
        self.topic_publisher.publish(routing_key,message)

    def respond_to_node_name_request(self, routing_key,body):
        self.publish(NODENAME_ROUTING_KEY,gos.gos_encode_string_message(self.node_name))

    def respond_to_node_info_request(self, routing_key,body):
        logger.debug("Responding to Info Request")
        return gos.gos_encode_json_message(self.get_json_description())

    def respond_to_service_name_request(self, routing_key,body):
        for key in self.topic_listener.service_callbacks.keys():
            self.publish(SERVICE_ROUTING_KEY,key)

    def respond_to_topics_published_request(self, method_frame,header_frame,body):
        ...
    
    def respond_to_topics_subscribed_request(self, method_frame,header_frame,body):
        ...

    def call_service(self,service_name,body=None):
        return self.topic_publisher.send_service_request(service_name,body)
    
    def call_action(self,action_name,message,progress_callback=None):
        result_event=threading.Event()
        my_result_array=[ None ]        
        def my_result_callback(key,message,event,result_array):
            logger.debug("my result callback")
            print("my result callback")
            result_array[0]=message            
            event.set()
        if progress_callback is not None:
            self.add_listener_callback(action_name+"/progress",progress_callback)
        self.topic_listener.dynamic_add_listener_callback(action_name+"/result",lambda a,b: my_result_callback(a,b,result_event,my_result_array))
        logger.debug("calling service {}".format(action_name+"/goal"))
        goal_response=self.call_service(action_name+"/goal",message)
        if goal_response==None:
            logger.warning("Error, response to action timed out")
            return None
        logger.debug("goal response is {}".format(goal_response))
        if goal_response["accepted"]==True:
            logger.debug("service called")
            while True:
                logger.debug("waiting")
                result_event.wait(timeout=1.0)
                if my_result_array[0] is None:
                    logger.debug("still waiting for action response")
                else:
                    self.topic_listener.dynamic_remove_listener_callback(action_name+"/result")
                    break
            #TODO unregister my result callback
            return my_result_array[0]
        else:
            logger.warning("action call failed")

    def add_service_callback(self,service_name,callback_function):        
        return self.topic_listener.add_service_callback(self.node_name+"/"+service_name,callback_function)

    def add_action_server(self,action_name,goal_callback_function,cancel_callback_function):
        goal_service=self.add_service_callback(action_name+"/goal",goal_callback_function)
        cancel_service=self.add_service_callback(action_name+"/cancel",cancel_callback_function)        
        progress_topic=self.node_name+"/"+action_name+"/progress"
        result_topic=self.node_name+"/"+action_name+"/result"        
        self.action_list.append(action_name)      
        return (goal_service,cancel_service,progress_topic,result_topic)

    def get_json_description(self):
        obj={}
        obj["Name"]=self.node_name
        services=[]
        for key in self.topic_listener.service_callbacks.keys():
            services.append(key)
        topics=[]
        for key in self.topic_listener.callbacks.keys():
            topics.append(key)
        obj["services"]=services
        obj["topics"]=topics
        return obj

class SimpleActionServer:
    def __init__(self,node):
        self.node=node
        self.should_cancel=False        
        self.action_request=None #it's a (key,message) pair
        self.should_quit=False
        self.thread = threading.Thread(target=self._thread_loop)        
        self.thread.daemon = True
        self.doing_action=threading.Condition()
        self.result_topic_map={}
        self.progress_topic_map={}


    def add_action(self,action_name):
        goal_name,cancel_name,progress_topic,result_topic=self.node.add_action_server(action_name,self.goal_callback,self.cancel_callback)
        self.result_topic_map[goal_name]=result_topic
        self.progress_topic_map[goal_name]=progress_topic        


    def goal_callback(self,routing_key,message):
        if self.doing_action.acquire(blocking=False):
            self.action_request=(routing_key,message)
            self.result_topic=self.result_topic_map[routing_key]
            self.progress_topic=self.progress_topic_map[routing_key]
            self.doing_action.notify()
            self.doing_action.release()
            logger.debug("accepted goal")
            return gos.gos_encode_json_message( {"accepted": True })
        else:
            logger.debug("Rejected goal, busy")
            return gos.gos_encode_json_message( {"accepted": False, "reason": "already {}".format(self.action_request)})

    def start(self):
        self.node.start()
        self.thread.start()

    def join(self):
        self.thread.join()


    def perform_action(self,key,message):
        logger.warning("Unhandled perform Action!!")
        ...
        #override this

    
    def cancel_callback(self,routing_key,message):
        self.should_cancel=True
        return gos.gos_encode_bool_message(True)
    
    def _thread_loop(self):
        self.doing_action.acquire()
        while not self.should_quit:
            while self.action_request is None and not self.should_quit:                
                self.doing_action.wait(timeout=0.1)
            if self.should_quit:
                break                
            self.should_cancel=False
            response=self.perform_action(self.action_request[0],self.action_request[1])
            self.node.publish(self.result_topic,response)
            self.action_request=None
            self.result_topic=None
            self.progress_topic=None