from socket import *
from threading import Thread, Lock, Event
import json
import signal
import zlib
import sys

transferStatus = {}
statusLock = Lock()
stopEvent = Event()

# Carregar configuração
with open('../config/config.json') as configFile:
    config = json.load(configFile)

def selectFile():
    #Função apenas para receber sinal (Ctrl + C) e fechar o servidor sem dar algum tipo de erro gigante.
    def signal_handler(sig, frame):
        print('Sinal de fechar a conexão recebido')
        stopEvent.set()
        sys.exit() 
    signal.signal(signal.SIGINT, signal_handler)
    
    while not stopEvent is set:
        fileName = input("Digite qual arquivo deseja fazer o backup ou digite sair caso não deseje mais transferir ou status caso deseje saber o status das transferências: ")
        if fileName.lower() == 'sair':
            print("Fechando...")
            break
        elif fileName.lower() == 'status':
            showStatus()
        else:
            thread = Thread(target=handle_middleware, args=(fileName,))
            thread.start()
            thread.join(timeout=5)
    
#Thread que chama o middleware enviando o arquivo
def handle_middleware(fileName):
    try:
        middlewareHost = config["middleware"]["host"]
        middlewarePort = config["middleware"]["port"]
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((middlewareHost, middlewarePort))
        with open(fileName, 'rb') as f:
            clientSocket.sendall(f"file:{fileName};comprimido;".encode())
            compressor = zlib.compressobj()
            while chunk := f.read(65536):
                compressedChunk = compressor.compress(chunk)
                if compressedChunk:
                    clientSocket.sendall(compressedChunk)
                with statusLock:
                    transferStatus[fileName] = "Enviando"
            clientSocket.sendall(compressor.flush())
        clientSocket.sendall(b"<FIM>")
        updateStatus(fileName, "Completo")
        print(f"Transferência do arquivo {fileName} concluída.")
        clientSocket.close()
    except FileNotFoundError:
        print(f"Arquivo {fileName} não encontrado.")
        updateStatus(fileName, "Arquivo não encontrado")
    except ConnectionRefusedError:
        print(f"Não foi possível conectar ao middleware em {middlewarePort} para transferir o arquivo {fileName}.")
        updateStatus(fileName, "Conexão recusada")
    except Exception as e:
        print(f"Erro ao enviar o arquivo {fileName}: {e}")
        updateStatus(fileName, "Erro")
        
#Atualiza o status do arquivo
def updateStatus(fileName, status):
    with statusLock:
        transferStatus[fileName] = status

#Caso o cliente queira saber o status das transferências
def showStatus():
    with statusLock:
        if not transferStatus:
            print("Nenhuma transferência em andamento ou concluída.")
        else:
            for file, status in transferStatus.items():
                print(f"Arquivo: {file}, Status: {status}")

selectFile()