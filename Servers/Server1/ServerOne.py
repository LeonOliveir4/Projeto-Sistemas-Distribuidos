from socket import *

#def isBackup:

def saveFile(file):
    combinedContent = ''.join(file)
    parts = combinedContent.split(';')
    file_dict = {}
    for part in parts:
        key, value = part.split(':', 1)
        file_dict[key] = value
    if 'name' in file_dict and 'content' in file_dict:
        fileName = file_dict['name']
        content = file_dict['content']
    if (content):
        with open(fileName, "w") as file:
            file.write(content)
            file.close()

#def callMiddleware(file)


def startServer():
    serverPort = 7002
    output = ''
    serverSocket = socket(AF_INET, SOCK_STREAM)
    #serverSocket.settimeout(None)
    serverSocket.bind(('localhost', serverPort))
    serverSocket.listen(1)
    fileContent = []
    try:
        print ('server Started')
        print ('If you want to close the connection press "ctrl" and "c" together then update the client page\n')
        connectionSocket, addr = serverSocket.accept()
        try:
            while True:
                value = connectionSocket.recv(1024)
                if not value:
                    break
                decoded_data = value.decode()
                if "<END>" in decoded_data:
                    fileContent.append(decoded_data.replace("<END>", ""))
                    break
                else:
                    fileContent.append(decoded_data)
            print (f'accepted connection from {addr}')
            for i in fileContent:
                output = output + str(i)
            saveFile(output)
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
        serverSocket.close()

startServer()