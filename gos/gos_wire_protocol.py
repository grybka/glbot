#Wire protocol for dropline
import struct
import json
import numpy as np

TYPE_BOOL=0
TYPE_STRING=1
TYPE_UINT=2
TYPE_INT=3
TYPE_DOUBLE=4
TYPE_JSON=5
TYPE_DOUBLE_NUMPY_ARRAY=6
TYPE_ANNOTATED_IMAGE=7

def get_message_type(message):
    #message is bytes
    return int.from_bytes(message[0:1],'little')

def gos_encode_bool_message(x):
    return int.to_bytes(TYPE_BOOL,1,'little')+bool.to_bytes(x,1,'little')

def gos_encode_string_message(x):
    return int.to_bytes(TYPE_STRING,1,'little')+x.encode('utf-8')
    
def gos_encode_uint_message(x):
    return int.to_bytes(TYPE_UINT,1,'little')+int.to_bytes(x,4,'little')

def gos_encode_int_message(x):
    return int.to_bytes(TYPE_INT,1,'little')+int.to_bytes(x,4,'little',signed=True)

def gos_encode_double_message(x):
    return int.to_bytes(TYPE_DOUBLE,1,'little')+struct.pack('<d',x)

def gos_encode_json_message(x):
    return int.to_bytes(TYPE_JSON,1,'little')+json.dumps(x).encode('ASCII')

def gos_encode_double_numpy_message(x):
    return int.to_bytes(TYPE_DOUBLE_NUMPY_ARRAY,1,'little')+x.astype('double').tobytes()

def gos_encode_annotated_image(thearray,metadatajson):
    nbytes=thearray.tobytes()
    metadatajson["shape"]=thearray.shape
    jbytes=json.dumps(metadatajson).encode('ASCII')
    #print("nbites len {}".format(len(nbytes)))
    #print("jbites len {}".format(len(jbytes)))
    return int.to_bytes(TYPE_ANNOTATED_IMAGE,1,'little')+\
           int.to_bytes(len(nbytes),4,'little')+\
           int.to_bytes(len(jbytes),4,'little')+\
           nbytes+\
           jbytes

    


def gos_decode(message): 
    mytype=get_message_type(message)
    if mytype==TYPE_BOOL:
        return bool.from_bytes(message[1:2],'little')
    elif mytype==TYPE_STRING:
        return message[1:].decode('utf-8')
    elif mytype==TYPE_UINT:
        return int.from_bytes(message[1:5],'little')
    elif mytype==TYPE_INT:
        return int.from_bytes(message[1:5],'little',signed=True)
    elif mytype==TYPE_DOUBLE:
        return struct.unpack('<d',message[1:9])[0]
    elif mytype==TYPE_JSON:
        return json.loads(message[1:])
    elif mytype==TYPE_DOUBLE_NUMPY_ARRAY:
        return np.frombuffer(message[1:])
    elif mytype==TYPE_ANNOTATED_IMAGE:
        nbytes_len=int.from_bytes(message[1:5],'little')
        jbytes_len=int.from_bytes(message[5:9],'little')
        #print("image bytes {}".format(nbytes_len))
        #print("json bytes {}".format(jbytes_len))
        nbytes=message[9:9+nbytes_len]
        jbytes=message[9+nbytes_len:11+nbytes_len+jbytes_len]
        image=np.frombuffer(nbytes,dtype=np.uint8)
        metadata=json.loads(jbytes)
        image.shape=metadata["shape"]
        return [image,metadata]
    else:
        raise Exception("data type: {} not supported".format(message[0]))
    
if __name__ == "__main__":
    a=True
    a="blarg"
    a=8
    a=9.42
    #ames=gos_encode_bool_message(a)
    #ames=gos_encode_string_message(a)
    #ames=gos_encode_int_message(a)
    #ames=gos_encode_double_message(a)
    #a=json.loads('{ "mydat": [ 0, 1, 2]}')
    #ames=gos_encode_json_message(a)
    a=np.array( (1.2,5))
    #a=np.array( (4,5))
    ames=gos_encode_double_numpy_message(a)
    amesdec=gos_decode(ames)
    print(amesdec)
    #Annotated image test
    test_image=np.zeros( (2,3,4),dtype=np.uint8 )
    test_annotation={ "bigness": 3}
    testmes=gos_encode_annotated_image(test_image,test_annotation)
    test_image_dec,test_annotation_dec=gos_decode(testmes)
    print("{}".format(test_image_dec))
    print("{}".format(json.dumps(test_annotation_dec)))