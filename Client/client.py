from socket import *
from asyncio import * 
def selectFile():
    fileName = input('input the file name (with the extensio) that you want to transfer: ')
    #print(f'{fileName} fileName\n')
    f = open(fileName[0:])
    print(f'{f} f\n')
    outputdata = f.read()
    #print(f'{outputdata} out\n')
    file = {"name": fileName, "content": outputdata}
    file_serialized = f"name:{file['name']};content:{file['content']}"
    file_encoded = file_serialized.encode()
    callMiddleware(file_encoded)

#This function will call the middleware sending the file
def callMiddleware(file):
    middlewarePort = 7001
    clientSocket = socket(AF_INET, SOCK_STREAM)
    #clientSocket.settimeout(None)
    clientSocket.connect((('localhost'), middlewarePort))
    # SendAll making the conection capable of send big files
    #for i in range(0, len(file)):
    #    clientSocket.send(file[i].encode())
    clientSocket.sendall(file)
    # Receive the message from the server (up to 1024 bytes)
    #modifiedMessage = clientSocket.recv(1024)
    #print(modifiedMessage)
    clientSocket.close

selectFile()