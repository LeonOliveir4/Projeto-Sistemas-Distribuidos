from socket import *
from threading import Thread
import signal
import sys

def handle_client(connectionSocket, addr):
    try:
        print(f"Connection from {addr}")
        serverSocket = callServer(addr)
        bytes = 0
        while True:
            chunk = connectionSocket.recv(65536)
            if not chunk:
                break
            bytes += len(chunk)
            serverSocket.sendall(chunk)
            if b"<END>" in chunk:
                print(f"End of transmission detected from {addr}")
                break

        print(f"Total bytes forwarded: {bytes}")
        serverSocket.sendall(b"<END>")
        modifiedMessage = serverSocket.recv(65536)
        print(f"Received confirmation from server for {addr}: {modifiedMessage.decode()}")
        serverSocket.close()
    except IOError:
        print("Closing connection - IOError")
    finally:
        print("Shutdown thread connection")
        connectionSocket.close()

def callServer(addr):
    serverPort = 7002
    print (f'accepted connection from {addr}')
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.connect((('localhost'), serverPort))
    return serverSocket

def startMiddleware():
    serverPort = 7001
    middlewareSocket = socket(AF_INET, SOCK_STREAM)
    middlewareSocket.bind(('localhost', serverPort))
    middlewareSocket.listen(5)
    
    def signal_handler(sig, frame):
        print('Shutdown Middleware')
        middlewareSocket.close()
        sys.exit()
    
    signal.signal(signal.SIGINT, signal_handler)
    try:
        print ('middleware Started')
        while True:
            connectionSocket, addr = middlewareSocket.accept()
            client_thread = Thread(target=handle_client, args=(connectionSocket, addr))
            client_thread.start()
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        # Shut down the server and log the shutdown
        print('Shutdown Middleware')
        middlewareSocket.close()

startMiddleware()