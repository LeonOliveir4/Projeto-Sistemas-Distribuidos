from socket import *
import zlib

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
        clientSocket.sendall(f"file:{fileName};comprimido;".encode())
        compressor = zlib.compressobj()
        while chunk := f.read(65536):
            compressedChunk = compressor.compress(chunk)
            if compressedChunk:
                clientSocket.sendall(compressedChunk)
        clientSocket.sendall(compressor.flush())
    clientSocket.sendall(b"<FIM>")
    clientSocket.close()

selectFile()