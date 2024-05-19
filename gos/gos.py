import argparse
import threading,queue
import Node
import time
import logging
import gos_wire_protocol as gos
import yaml
import json
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.WARNING)
logger=logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='sub-command help',dest='command')
parser_node = subparsers.add_parser('node', help='node help')
parser_node.add_argument("subcommand")
parser_node.add_argument("nodename",default="None",nargs='?')
parser_service = subparsers.add_parser('service', help='service help')
parser_service.add_argument("subcommand")
parser_service.add_argument("servicename",default="None",nargs='?')
parser_service.add_argument("servicearg",default="None",nargs='?')
parser_action = subparsers.add_parser('action', help='action help')
parser_action.add_argument("subcommand")
parser_action.add_argument("actionname",default="None",nargs='?')
parser_action.add_argument("actionarg",default="None",nargs='?')





args=parser.parse_args()
print("{}".format(args))
node=Node.Node("gos command line","10.0.0.134")

def guess_command_to_message(x):
    try:
        result=float(x)
        if result.is_integer():
            logger.debug("sending integer {}".format(int(result)))
            return gos.gos_encode_int_message(int(result))
        return gos.gos_encode_double_message(result)
    except ValueError:
        try:
            result=json.loads(x)
            return gos.gos_encode_json_message(result)
        except ValueError:
            return gos.gos_encode_string_message(x)
        
def get_all_nodes():
    node_queue=queue.Queue()
    def collect_response(key,message):        
        #print("response")
        node_queue.put(message)
    node.add_listener_callback(Node.NODENAME_ROUTING_KEY, collect_response)    
    node.start()
    #time.sleep(0.5)
    node.wait_until_ready()
    node.publish(Node.NODENAME_QUERY_ROUTING_KEY,gos.gos_encode_bool_message(True))
    time.sleep(1)
    return list(node_queue.queue)

def list_nodes(): 
    node_list=get_all_nodes()   
    node.disconnect()
    print("Nodes: ")
    for n in node_list:
        print(" {}".format(n))

def list_services():    
    node_queue=queue.Queue()
    def collect_response(key,message):        
        #print("response")
        node_queue.put(message.decode("UTF-8"))
    node.add_listener_callback(Node.SERVICE_ROUTING_KEY, collect_response)    
    node.start()
    #time.sleep(0.5)
    node.wait_until_ready()
    node.publish(Node.SERVICE_QUERY_ROUTING_KEY,"")
    time.sleep(1)
    node.disconnect()
    print("Services: ")
    while not node_queue.empty():
        print(" {}".format(node_queue.get()))

def get_node_info(nodename):
    servicename=nodename+"/"+Node.NODEINFO_QUERY_ROUTING_KEY
    #print("calling service: {}".format(servicename))
    resp=node.call_service(servicename,gos.gos_encode_string_message(""))
    return resp

def list_actions():
    ...

def print_usage():
    print("options:")
    print(" node ")
    print("   list") 
    print("   info")    
    print(" service ")
    print("   list")
    print("   call")
    print(" action")
    print("   call")

if args.command=="node":    
    if args.subcommand=="list":
        list_nodes()
        exit()
    if args.subcommand=="info":
        node.start()
        node.wait_until_ready()
        resp=get_node_info(args.nodename)
        node.disconnect()
        print(yaml.dump(resp))
        exit()
    else:
        print_usage()
        exit()
elif args.command=="service":
    if args.subcommand=="list":
        list_services()
        exit()
    if args.subcommand=="call":
        node.start()
        node.wait_until_ready()
        result=node.call_service(args.servicename,guess_command_to_message(args.servicearg))
        print("Result was {}".format(result))
        node.disconnect()
        exit()
    else:
        print_usage()
        exit()
elif args.command=="action":
    if args.subcommand=="call":
        node.start()
        node.wait_until_ready()
        def print_progress(key,message):
            print("Progress: {}".format(message))
        result=node.call_action(args.actionname,guess_command_to_message(args.actionarg),print_progress)
        print("result was {}".format(result))
#        is_done=False
#
#def print_result(key,message):
#            global is_done
#            is_done=True
#            print("Result: {}".format(message))
 #       node.add_listener_callback(args.actionname+"/progress", print_progress)
#        node.add_listener_callback(args.actionname+"/result", print_result)
#        print("calling {}".format(args.actionname+"/goal"))
#        node.start()
#        node.wait_until_ready()
#        node.call_service(args.actionname+"/goal",guess_command_to_message(args.actionarg))
#        while is_done==False:
#            time.sleep(0.1)
        node.disconnect()
        exit()


        ...
else:
    print_usage()
    exit()
    