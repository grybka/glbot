import threading,queue
import logging
import socket
import numpy as np
import select
import sys,time
from MJPEG_Frame import MJPEG_Frame
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class MJPEG_server:
    def __init__(self):
        self.should_quit = False
        maxsize=10
        self.output_queue=queue.Queue(maxsize=maxsize)
        self.is_connected=False
        self.server_sock=None
        self.sender_thread=None

    def _sender_thread_loop(self):
        #cleare the queue
        while not self.output_queue.empty():
            self.output_queue.get(block=False)
        while not self.should_quit:
            self.is_connected=True
            try:
                to_send=self.output_queue.get(timeout=1)
                length,data=to_send.serialize()
                self.sock.sendall(int.to_bytes(length,4,'little',signed=False))
                self.sock.sendall(data)
            except queue.Empty:
                ...
            except socket.error as e:
                logger.error("sender socket error {}, closing".format(e))
                break
        self.is_connected=False


    def quit(self):
        self.should_quit=True
        if self.sender_thread is not None:
            self.sender_thread.join()                
        if self.server_sock is not None:
            self.server_sock.close()

    def _thread_loop_server(self):
        while not self.should_quit:
            logger.debug("listening for connections")
            try:
                (self.sock, address) = self.server_sock.accept()

                self.sender_thread = threading.Thread(target=self._sender_thread_loop)
                self.sender_thread.daemon = True
                self.sender_thread.start()

                self.sender_thread.join()
                self.sock.close()
                self.sock=None
            except socket.timeout:
                ... #this is fine, just retry
            except Exception as e:
                logger.warning("unhandled exception in accept, closing connection")
                logger.warning("{}".format(e))

                #self.should_quit=True
        self.server_sock.close()

    def start_server(self,port=23033):
        logger.info("creating server socket")
        self.host = "10.0.0.134"
        self.port=port
        self.server_sock= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.server_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        #self.server_sock=socket.create_server( (self.host,self.port), reuse_port=True )
        self.server_sock.settimeout(5)
        logger.info("binding to {} {}".format(self.host,port))
        self.server_sock.bind((self.host, port))

        logger.info("listening")
        self.server_sock.listen(1) #accept only one connection at a time
        logger.info("thread starting")
        self.thread = threading.Thread(target=self._thread_loop_server)
        self.thread.daemon = True
        self.thread.start()

if __name__=="__main__":
    test_port=23033
    print("creating server")
    server=MJPEG_server()
    print("starting server")
    server.start_server(port=test_port)
    last_send=0
    frame=np.zeros( (480,640,3))
    my_frame=MJPEG_Frame(frame)
    try:
        while True:
            time.sleep(0.1)
            if time.time()>last_send+1:                
                print("time to send")
                server.output_queue.put(my_frame)
                last_send=time.time()
                #print("server sends")            
    except KeyboardInterrupt:
        logger.error("Keyboard interrupt")
    finally:
        server.quit()