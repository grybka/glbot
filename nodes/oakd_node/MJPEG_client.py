import threading,queue
import logging
import socket
import select
import sys,time
from MJPEG_Frame import MJPEG_Frame

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class MJPEG_client:
    def __init__(self,debug=False,maxsize=10,callback=None):
        self.debug=debug
        self.sock=None
        self.should_quit = False
        self.recver_thread=None
        self.frame_callback=callback

    def start_client(self,host,port):
        self.host=host
        self.port=port
        #connect to server
        logger.info("creating client socket")
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(5)
        logger.info("connecting")
        conninfo= self.sock.connect((self.host,self.port))

        logger.info("starting thread")

        self.recver_thread = threading.Thread(target=self._recver_thread_loop)
        self.recver_thread.daemon = True
        self.recver_thread.start()

    def _recver_thread_loop(self):
        while not self.should_quit:
            inputs=[self.sock]
            readable, writable, exceptional = select.select(inputs, [], inputs,5) #timeout 5 seconds
            if self.sock in exceptional:
                logger.error("Exception in socket")
            if self.sock in readable:
                try:
                    length=self.sock.recv(4)
                    if length==b'':
                        logger.info("Closing connection to ".format(self.host))
                        break
                    read_size=int.from_bytes(length,byteorder='little')
                    logger.debug("readed length {}".format(read_size))
                    data=b''
                    while(read_size>0):
                        newdata=self.sock.recv(read_size)
                        if newdata==b'':
                            logger.info("Closing connection to ".format(self.host))
                            break
                        data+=newdata
                        read_size=read_size-len(newdata)
                except Exception as error:
                    logger.error("Recvr error, closing")
                    break
                try:
                    self.frame_callback(MJPEG_Frame.unserialize(data))                                        
                except Exception as error:
                    logger.error("Error parsing")
                    logger.exception(error)
                
    def quit(self):
        self.should_quit=True
        self.recver_thread.join()
            
if __name__ == '__main__':
    #logger.basicConfig(level=logging.WARNING)
    test_port=23033
    def callback(data):
        logger.warning("got a frame {}".format(data.frame.shape))        
    client=MJPEG_client(callback=callback)
    client.start_client("localhost",test_port)
    print("client started")
    last_send=0


    try:
        while True:
            time.sleep(0.01)                
    except KeyboardInterrupt:
        logger.error("Keyboard interrupt")
    finally:
        client.quit()