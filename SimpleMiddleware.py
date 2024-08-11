from socket import *
from threading import Thread, Event, Lock
import json
import signal
import sys
import random

# Carregar configurações do sistema
with open('config/systemConfig.json') as config_file:
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
        print(f"Status do servidor {serverAddress}: {data}")  # Log do status do servidor
        return data
    except Exception as e:
        print(f"Erro ao conectar ao servidor {serverAddress}: {e}")
        return None

# Atualiza lista de servidores carregados
def atualizaInfosDoServer():
    with loadLock:
        for server in servers:
            loadInfo = getServerStatus(server)
            if loadInfo:
                serverLoads[server] = loadInfo
            print(f"Info atualizada do servidor {server}: {loadInfo}")  # Log de atualização de informações

# Seleciona servidor para enviar o arquivo
def selectServers():
    try:
        if not serverLoads:
            if len(servers) < 2:
                raise ValueError("Número insuficiente de servidores para efetuar backup.")
            
            primary = random.choice(servers)
            backup = random.choice([s for s in servers if s != primary])
            print(f"Servidores selecionados (sem carga): Primário={primary}, Backup={backup}")  # Log dos servidores selecionados
            return primary, backup
        
        primary = min(serverLoads, key=lambda k: float(serverLoads[k].split(',')[0].split(':')[1].strip().replace('%', '')))
        
        backup_candidates = [s for s in serverLoads if s != primary]
        
        if not backup_candidates:
            raise ValueError("Número insuficiente de servidores para efetuar backup.")
        
        backup = min(backup_candidates, key=lambda k: float(serverLoads[k].split(',')[0].split(':')[1].strip().replace('%', '')))
        print(f"Servidores selecionados (com carga): Primário={primary}, Backup={backup}")  # Log dos servidores selecionados com base na carga
        return primary, backup

    except ValueError as ve:
        print(f"Erro na seleção de servidores: {ve}")
        raise
    except Exception as e:
        print(f"Erro inesperado na seleção de servidores: {e}")
        raise

# Thread para lidar com o cliente
def handle_client(connectionSocket, addr):
    try:
        print(f"Conexão de {addr} recebida.")  # Log da conexão do cliente
        atualizaInfosDoServer()
        primary, backup = selectServers()

        # Envia as informações do servidor primário para o cliente
        response = json.dumps({"primary": primary})
        connectionSocket.sendall(response.encode())
        print(f"Informações do servidor primário {primary} enviadas para o cliente {addr}.")  # Log de envio para o cliente

        # Envia as informações do servidor de backup diretamente para o servidor primário
        primarySocket = socket(AF_INET, SOCK_STREAM)
        primarySocket.connect(primary)
        backup_info = json.dumps({"backup": backup})
        primarySocket.sendall(backup_info.encode())
        print(f"Informações do servidor de backup {backup} enviadas para o servidor primário {primary}.")  # Log de envio do backup
        primarySocket.close()

    except IOError as io_error:
        print(f"Erro de I/O ao lidar com o cliente {addr}: {io_error}")  # Log detalhado em caso de erro de I/O
    except Exception as e:
        print(f"Erro inesperado ao lidar com o cliente {addr}: {e}")  # Log detalhado para qualquer outro tipo de erro
    finally:
        print(f"Fechando conexão com o cliente {addr}.")  # Log ao fechar a conexão
        connectionSocket.close()

# Inicia o Middleware
def startMiddleware():
    serverPort = 7001
    middlewareSocket = socket(AF_INET, SOCK_STREAM)
    middlewareSocket.bind(('localhost', serverPort))
    middlewareSocket.listen(5)
    middlewareSocket.settimeout(1)
    
    def signal_handler(sig, frame):
        print('Sinal de fechar a conexão recebido')
        stopEvent.set()
        middlewareSocket.close()
        sys.exit()
    
    signal.signal(signal.SIGINT, signal_handler)
    try:
        print('Middleware Iniciado na porta', serverPort)
        while not stopEvent.is_set():
            try:
                connectionSocket, addr = middlewareSocket.accept()
                print(f"Nova conexão de {addr}.")  # Log de nova conexão
                client_thread = Thread(target=handle_client, args=(connectionSocket, addr))
                client_thread.start()
            except timeout:
                continue
    except Exception as e:
        print(f"Erro no middleware: {e}")  # Log de erro geral no middleware
    finally:
        print('Desligando middleware')
        middlewareSocket.close()

startMiddleware()