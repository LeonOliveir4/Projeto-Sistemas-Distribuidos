from socket import *

def callServer(file, addr):
    #combinedContent = ''.join(file)
    #parts = combinedContent.split(';')
    #file_dict = {}
    #for part in parts:
    #    key, value = part.split(':', 1)
    #    file_dict[key] = value
    #if 'name' in file_dict and 'content' in file_dict:
    #    file_serialized =  f"name:{file_dict['name']};content:{file_dict['content']}"
    serverPort = 7002
    output = ''
    print (f'accepted connection from {addr}')
    serverSocket = socket(AF_INET, SOCK_STREAM)
    #serverSocket.settimeout(None)
    serverSocket.connect((('localhost'), serverPort))
    # SendAll making the conection capable of send big files
    for i in file:
        output = output + str(i)
    serverSocket.sendall((output + "<END>").encode())
    # Receive the message from the server (up to 1024 bytes)
    modifiedMessage = serverSocket.recv(1024)
    #print(modifiedMessage)
    serverSocket.close

def startMiddleware():
    serverPort = 7001
    middlewareSocket = socket(AF_INET, SOCK_STREAM)
    #middlewareSocket.settimeout(None)
    middlewareSocket.bind(('localhost', serverPort))
    middlewareSocket.listen(1)
    fileContent = []
    try:
        print ('middleware Started')
        print ('If you want to close the connection press "ctrl" and "c" together then update the client page\n')
        connectionSocket, addr = middlewareSocket.accept()
        try:
            while True:
                file = connectionSocket.recv(1024)
                if not file:
                    break
                fileContent.append(file.decode())
            callServer(fileContent, addr)
        except IOError:
            print("Closing connection - Keyboard Interrupt")
            #Handle the case of error between transaction with client or server
            #connectionSocket.send(b"HTTP/1.1 404 Not Found\r\n")
            #connectionSocket.send(b"Content-Type: text/html\r\n\r\n")
            #connectionSocket.send(b"<html><body><h1>404 Not Found</h1></body></html>")
        finally:
            # Shut down the conection
            print('Shutdown conection')
            connectionSocket.close()
    except KeyboardInterrupt:
        # Interrupt the server loop
        print("Closing connection - Keyboard Interrupt")
    finally:
        # Shut down the server and log the shutdown
        print('Shutdown server')
        middlewareSocket.close()

startMiddleware()