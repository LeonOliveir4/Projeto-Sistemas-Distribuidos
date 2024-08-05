from socket import *
from threading import Thread, Event, Lock
import json
import signal
import sys
import time

with open('config/config.json') as config_file:
    config = json.load(config_file)
    
stopEvent = Event()
servers = [(server["host"], server["port"]) for server in config["servers"]]
serverLoads = {}
loadLock = Lock()

# Método que pega o status do servidor para selecionar para qual será enviado o arquivo
def getServerStatus(serverAddress):
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect(serverAddress)
        clientSocket.sendall(b"STATUS")
        data = clientSocket.recv(1024).decode()
        clientSocket.close()
        return data
    except Exception as e:
        print(f"Erro ao conectar ao servidor {serverAddress}: {e}")
        return None

# Atualiza lista de servidores carregados
def atualizaInfosDoServer():
    with loadLock:
        for server in servers:
            load_info = getServerStatus(server)
            if load_info:
                serverLoads[server] = load_info

# Seleciona servidor para enviar o arquivo
def selectServer():
    with loadLock:
        if not serverLoads:
            return servers[0]  # Se não houver informações, use o primeiro servidor
        return min(serverLoads, key=lambda k: float(serverLoads[k].split(',')[0].split(':')[1].strip().replace('%', '')))

# Thread que vai receber e já enviar o arquivo ao servidor
def handle_client(connectionSocket, addr):
    try:
        print(f"Conexão de {addr}")
        atualizaInfosDoServer()  # Atualiza as informações dos servidores a cada nova conexão
        server = selectServer()
        print(f"Encaminhando para o servidor: {server} com carga: {serverLoads.get(server, 'N/A')}")
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.connect(server)
        bytes = 0
        while not stopEvent.is_set():
            chunk = connectionSocket.recv(65536)
            if not chunk:
                break
            bytes += len(chunk)
            serverSocket.sendall(chunk)
            if b"<FIM>" in chunk:
                print(f"Fim da transmissão de arquivos proveniente de {addr}")
                break
        print(f"bytes enviados: {bytes}")

        modifiedMessage = b""
        while True:
            chunk = serverSocket.recv(65536)
            if not chunk:
                break
            modifiedMessage += chunk
            if b"<CONFIRMADO>" in modifiedMessage:
                print(f"Recebendo confirmação do server {addr}")
                break
        serverSocket.close()
    except IOError:
        print("Fechando conexão - IOError")
    finally:
        print("Fechando conexão de thread do middleware")
        connectionSocket.close()

# Inicia o Middleware
def startMiddleware():
    serverPort = 7001
    middlewareSocket = socket(AF_INET, SOCK_STREAM)
    middlewareSocket.bind(('localhost', serverPort))
    middlewareSocket.listen(5)
    middlewareSocket.settimeout(1)
    
    # Função apenas para parar o middleware caso queira (CTRL + C)
    def signal_handler(sig, frame):
        print('Sinal de fechar a conexão recebido')
        stopEvent.set()
        middlewareSocket.close()
        sys.exit()
    
    signal.signal(signal.SIGINT, signal_handler)
    try:
        print('Middleware Iniciado')
        while not stopEvent.is_set():
            try:
                connectionSocket, addr = middlewareSocket.accept()
                client_thread = Thread(target=handle_client, args=(connectionSocket, addr))
                client_thread.start()
            except timeout:
                continue
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        print('Desligando middleware')
        middlewareSocket.close()

startMiddleware()
