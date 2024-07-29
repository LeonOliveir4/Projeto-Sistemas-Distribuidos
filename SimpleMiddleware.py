from socket import *
from threading import Thread
import signal
import sys

def handle_client(connectionSocket, addr):
    try:
        data = b''
        while True:
            chunk = connectionSocket.recv(8192)
            data += chunk
            if b"<FIM>" in data:
                data = data[:data.find(b"<FIM>")]
                break
        separatorIndex = data.find(b';')
        fileName = data[5: separatorIndex].decode()
        fileContent = data[separatorIndex + 1:]
        
        serverSocket = callServer(addr)
        serverSocket.sendall(f"file:{fileName};".encode())
        serverSocket.sendall(fileContent)
        while chunk := connectionSocket.recv(8192):
            if b"<FIM>" in chunk:
                serverSocket.sendall(chunk[:chunk.find(b"<FIM>")])
                break
            serverSocket.sendall(chunk)
        serverSocket.sendall(b"<FIM>")
        modifiedMessage = serverSocket.recv(8192)
        print(modifiedMessage.decode())
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