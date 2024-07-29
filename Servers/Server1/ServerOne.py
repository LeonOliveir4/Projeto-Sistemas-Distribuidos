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
        saveFile(data, connectionSocket)
        connectionSocket.send(b"File received and saved successfully")
    except IOError:
        print("Closing connection - IOError")
    finally:
        print('Shutdown thread connection')
        connectionSocket.close()

#def isBackup:

def saveFile(file, connectionSocket):
    separatorIndex = file.find(b';')
    if separatorIndex == -1:
        print('Invalid file format received')
        return

    fileName = file[5:separatorIndex].decode()  # Extract file name
    fileContent = file[separatorIndex + 1:]  # Extract file content

    with open(fileName, "wb") as file:
        file.write(fileContent)
        while chunk := connectionSocket.recv(8192):
            if b"<FIM>" in chunk:
                file.write(chunk[:chunk.find(b"<FIM>")])
                break
            file.write(chunk)
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