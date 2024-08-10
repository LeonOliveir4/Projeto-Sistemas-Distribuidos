from socket import *
from threading import Thread, Event, Lock
import json
import signal
import sys
import random

with open('config/config.json') as config_file:
    config = json.load(config_file)
    
stopEvent = Event()
servers = [(server["host"], server["port"]) for server in config["servers"]]
loadLock = Lock()
serverLoads = {}

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
# Para isso é feito o seguinte -> Se tem info dos servidores, pega o que tem mais utilização disponível de cpu (serverLoads[k])
# Para o servidor de backup pega o segundo menor (diferente do primeiro)
# Se não tem info, pega randomicamente o principal e depois o de backup desde que seja diferente
def selectServers():
    try:
        if not serverLoads:
            # Verifica se há pelo menos dois servidores disponíveis
            if len(servers) < 2:
                raise ValueError("Número insuficiente de servidores para replicação.")
            
            primary = random.choice(servers)
            replica = random.choice([s for s in servers if s != primary])
            return primary, replica
        
        # Quando há dados de carga disponíveis
        primary = min(serverLoads, key=lambda k: float(serverLoads[k].split(',')[0].split(':')[1].strip().replace('%', '')))
        
        # Filtra o servidor primário para escolher o de backup
        replica_candidates = [s for s in serverLoads if s != primary]
        
        # Verifica se há pelo menos um servidor disponível para backup
        if not replica_candidates:
            raise ValueError("Número insuficiente de servidores para replicação.")
        
        replica = min(replica_candidates, key=lambda k: float(serverLoads[k].split(',')[0].split(':')[1].strip().replace('%', '')))
        return primary, replica

    except ValueError as ve:
        print(f"Erro: {ve}")
        raise  # Re-levanta a exceção para lidar mais adiante ou para debugging
    except Exception as e:
        print(f"Erro inesperado na seleção de servidores: {e}")
        raise  # Re-levanta a exceção para que seja tratada mais adiante

# Thread para lidar com o cliente
def handle_client(connectionSocket, addr):
    try:
        print(f"Conexão de {addr}")
        atualizaInfosDoServer()  # Atualiza as informações dos servidores a cada nova conexão
        primary, replica = selectServers()
        response = json.dumps({"primary": primary, "replica": replica})
        connectionSocket.sendall(response.encode())
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
