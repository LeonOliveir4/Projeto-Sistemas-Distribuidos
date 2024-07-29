from socket import *
from threading import Thread
import signal
import sys
import zlib

def handle_client(connectionSocket, addr):
    try:
        header = b''
        while not header.endswith(b';comprimido;'):
            headerChunk = connectionSocket.recv(1)
            if not headerChunk:
                raise IOError("Connection closed before header was fully received")
            header += headerChunk
        fileName = header.split(b';')[0].split(b':')[1].decode()
        decompressor = zlib.decompressobj()
        data = b''
        while True:
            chunk = connectionSocket.recv(65536)
            if not chunk:
                break
            if b"<FIM>" in data:
                data += decompressor.decompress(chunk[:chunk.find(b"<FIM>")])
                break
            data += decompressor.decompress(chunk)
        data += decompressor.flush()
        print(f"Finished receiving and decompressing file: {fileName}")
        saveFile(fileName, data, connectionSocket)
        connectionSocket.send(b"File received and saved successfully")
    except IOError:
        print("Closing connection - IOError")
    finally:
        print('Shutdown thread connection')
        connectionSocket.close()

#def isBackup:

def saveFile(fileName, fileContent, connectionSocket):
    with open(fileName, "wb") as file:
        file.write(fileContent)
    print(f'File {fileName} saved successfully.')

#def callMiddleware(file)


def startServer():
    serverPort = 7002
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('localhost', serverPort))
    serverSocket.listen(5)
    
    def signal_handler(sig, frame):
        print('Shutdown Server')
        serverSocket.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    try:
        print ('server Started')
        while True: 
            connectionSocket, addr = serverSocket.accept()
            client_thread = Thread(target=handle_client, args=(connectionSocket, addr))  
            client_thread.start()
            connectionSocket.send(b"File received and saved successfully.")
    except KeyboardInterrupt:
        # Interrupt the server loop
        print("Closing connection - Keyboard Interrupt")
    finally:
        # Shut down the server and log the shutdown
        print('Shutdown server')
        serverSocket.close()

startServer()