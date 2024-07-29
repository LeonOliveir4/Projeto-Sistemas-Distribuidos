from socket import *

def selectFile():
    while True:
        fileName = input("Diga qual arquivo deseja fazer o backup: ")
        callMiddleware(fileName)
        if fileName.lower() == 'sair':
            print("Fechando...")
            break
    
#This function will call the middleware sending the file
def callMiddleware(fileName):
    middlewarePort = 7001
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((('localhost'), middlewarePort))
    with open(fileName, 'rb') as f:
        clientSocket.sendall(f"file:{fileName};".encode())
        while chunk := f.read(8192):
            clientSocket.sendall(chunk)
    clientSocket.sendall(b"<FIM>")
    clientSocket.close()

selectFile()