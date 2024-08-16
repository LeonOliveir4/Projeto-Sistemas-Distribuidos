from socket import *
from threading import Thread, Event, Lock
import os
import json
import signal
import sys
import random

# Obter o diretório atual do script
currentDir = os.path.dirname(os.path.abspath(__file__))

# Montar o caminho completo para o arquivo de configuração
configPath = os.path.join(currentDir, 'systemConfig.json')

# Carregar configurações do sistema
with open(configPath) as configFile:
    config = json.load(configFile)
    
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
        # Se não houver informações de carga, escolher aleatoriamente
        if not serverLoads:
            if len(servers) < 2:
                raise ValueError("Número insuficiente de servidores para efetuar backup.")
            
            primary = random.choice(servers)
            backup = random.choice([s for s in servers if s != primary])
            print(f"Servidores selecionados (sem carga): Primário={primary}, Backup={backup}")  # Log dos servidores selecionados
            return primary, backup
        
        # Analisando CPU, Memória e Threads Ativas
        def parseLoadInfo(load_info):
            parts = load_info.split(',')
            try:
                cpuUsage = float(parts[0].split(':')[1].strip().replace('%', ''))
                memUsage = float(parts[1].split(':')[1].strip().replace('%', ''))
                threadsActive = int(parts[2].split(':')[1].strip())
                return cpuUsage, memUsage, threadsActive
            except ValueError as e:
                print(f"Erro ao analisar as informações de carga: {e}")
                return None

        # Filtrar servidores válidos (com dados de carga válidos)
        validServers = {s: load for s, load in serverLoads.items() if parseLoadInfo(load)}

        # Se não restar nenhum servidor válido, tentar novamente
        if len(validServers) < 2:
            print("Tentando reavaliar os servidores devido a dados inválidos.")
            atualizaInfosDoServer()
            validServers = {s: load for s, load in serverLoads.items() if parseLoadInfo(load)}

            if len(validServers) < 2:
                raise ValueError("Número insuficiente de servidores válidos após reavaliação.")

        # Função para calcular a margem de diferença aceitável
        def withinMargin(server1, server2, margin_cpu=3.0, margin_mem=1.0):
            cpu1, mem1, _ = parseLoadInfo(validServers[server1])
            cpu2, mem2, _ = parseLoadInfo(validServers[server2])

            # Verifica se a diferença de CPU e Memória está dentro das margens permitidas
            return abs(cpu1 - cpu2) <= margin_cpu and abs(mem1 - mem2) <= margin_mem
        
        # Função para selecionar o melhor servidor considerando CPU, Memória e Threads Ativas
        def selectBestServer(server_list):
            # Ordena primeiro por CPU e Memória
            sortedServers = sorted(server_list, key=lambda k: (
                parseLoadInfo(validServers[k])[0],  # Menor CPU
                parseLoadInfo(validServers[k])[1]   # Menor Memória
            ))

            # Seleciona o melhor servidor com base na menor CPU e Memória
            best_server = sortedServers[0]

            # Verifica se os dois primeiros servidores têm uma diferença dentro das margens
            if len(sortedServers) > 1 and withinMargin(sortedServers[0], sortedServers[1]):
                # Se dentro da margem, seleciona o que tem menos threads ativas
                best_server = min(sortedServers[:2], key=lambda k: parseLoadInfo(validServers[k])[2])

            return best_server

        # Seleciona o servidor primário
        primary = selectBestServer(validServers.keys())

        # Filtra os servidores para escolher o de backup, excluindo o primário
        backup_candidates = [s for s in validServers if s != primary]
        
        if not backup_candidates:
            raise ValueError("Número insuficiente de servidores para efetuar backup.")
        
        # Seleciona o servidor de backup
        backup = selectBestServer(backup_candidates)
        
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
        backupInfo = json.dumps({"backup": backup})
        primarySocket.sendall(backupInfo.encode())
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
    middlewareHost = config["middleware"]["host"]
    middlewarePort = config["middleware"]["port"]
    serverPort = middlewarePort
    middlewareSocket = socket(AF_INET, SOCK_STREAM)
    middlewareSocket.bind((middlewareHost, serverPort))
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