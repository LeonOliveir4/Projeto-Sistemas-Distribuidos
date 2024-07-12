from socket import *

#def isBackup:

#def saveFile():

#def callMiddleware(file)


def startServer():
    serverPort = 7002
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', serverPort))
    serverSocket.listen(1)
    try:
        while True:
            print ('server Started')
            print ('If you want to close the connection press "ctrl" and "c" together then update the client page\n')
            connectionSocket, addr = serverSocket.accept
            try:    
                file = connectionSocket.recv(1024)
            except IOError:
                #Handle the case of error between transaction with client or server
                connectionSocket.send(b"HTTP/1.1 404 Not Found\r\n")
                connectionSocket.send(b"Content-Type: text/html\r\n\r\n")
                connectionSocket.send(b"<html><body><h1>404 Not Found</h1></body></html>")
    except KeyboardInterrupt:
        # Interrupt the server loop
        print("Closing connection - Keyboard Interrupt")
    finally:
        # Shut down the server and log the shutdown
        print('Shutdown server')
        serverSocket.close()