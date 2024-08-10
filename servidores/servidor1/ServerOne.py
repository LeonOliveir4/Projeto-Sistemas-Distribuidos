import json
import os
import signal
import sys
import psutil
import zlib
from socket import *
from threading import Thread, Event
import select

stopEvent = Event()

# Thread que vai realizar o recebimento, decompressão e chamar o método para salvar o arquivo
def handle_client(connectionSocket, addr, rootDir, middlewareHost, middlewarePort, initialData):
    try:
        header = initialData
        while b';comprimido;' not in header:
            headerChunk = connectionSocket.recv(1)
            if not headerChunk:
                raise IOError("Conexão fechada antes de header ser recebido")
            header += headerChunk
        header_parts = header.split(b';comprimido;', 1)
        file_info = header_parts[0]
        file_data = header_parts[1] if len(header_parts) > 1 else b''
        
        try:
            fileName = file_info.decode().split(':')[1]
        except UnicodeDecodeError:
            print("Erro ao decodificar o header")
            connectionSocket.close()
            return
        
        decompressor = zlib.decompressobj()
        data = decompressor.decompress(file_data)
        
        while True:
            ready_to_read, _, _ = select.select([connectionSocket], [], [], 1)
            if ready_to_read:
                chunk = connectionSocket.recv(65536)
                if not chunk:
                    break
                if b"<FIM>" in chunk:
                    data += decompressor.decompress(chunk[:chunk.find(b"<FIM>")])
                    break
                data += decompressor.decompress(chunk)
            else:
                break

        data += decompressor.flush()
        print(f"Arquivo recebido e decomprimido: {fileName}")
        
        # Tenta salvar o arquivo e trata qualquer erro que ocorra
        try:
            saveFile(fileName, data, rootDir)
            connectionSocket.send(b"Arquivo recebido e salvo com sucesso")
        except Exception as e:
            print(f"Erro ao salvar o arquivo {fileName}: {e}")
            connectionSocket.send(b"Erro ao salvar o arquivo")

        # Solicita ao middleware o servidor de réplica
        replica = get_replica_server(middlewareHost, middlewarePort)
        if replica:
            send_replica(fileName, data, replica)

        connectionSocket.send(b"<CONFIRMATION>")
    except IOError:
        print("Fechando conexão - IOError")
    except Exception as e:
        print(f"Erro inesperado ao lidar com o cliente {addr}: {e}")
    finally:
        print('Fechando conexão de thread do servidor')
        connectionSocket.close()

# Irá salvar o arquivo
def saveFile(fileName, fileContent, rootDir):
    filePath = os.path.join(rootDir, fileName)
    with open(filePath, "wb") as file:
        file.write(fileContent)
    print(f'O arquivo {fileName} foi salvo com sucesso.')

# Pega o status de uso do servidor para enviar ao middleware
def getServerStatus():
    cpu_usage = psutil.cpu_percent(interval=1)
    mem_usage = psutil.virtual_memory().percent
    return f"CPU: {cpu_usage}%, Memory: {mem_usage}%" 

# Thread para enviar status ao Middleware       
def handle_status(connectionSocket):
    load_info = getServerStatus().encode()
    connectionSocket.sendall(load_info)
    connectionSocket.close()

# Solicita ao middleware o servidor de réplica
def get_replica_server(middlewareHost, middlewarePort):
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((middlewareHost, middlewarePort))
        clientSocket.sendall(b"GET_REPLICA_SERVER")
        response = clientSocket.recv(1024)
        replica_info = json.loads(response.decode())
        clientSocket.close()
        return tuple(replica_info["replica"])
    except Exception as e:
        print(f"Erro ao obter servidor de réplica: {e}")
        return None

# Envia réplica ao servidor de réplica
def send_replica(fileName, data, replica):
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect(replica)
        header = f"file:{fileName};comprimido;".encode()
        clientSocket.sendall(header)
        
        compressor = zlib.compressobj()
        offset = 0
        chunk_size = 65536
        while offset < len(data):
            chunk = data[offset:offset+chunk_size]
            compressedChunk = compressor.compress(chunk)
            if compressedChunk:
                clientSocket.sendall(compressedChunk)
            offset += chunk_size
        
        clientSocket.sendall(compressor.flush())
        clientSocket.sendall(b"<FIM>")
        
        # Aguardar confirmação da réplica
        confirmation = clientSocket.recv(1024)
        print(f"Confirmação recebida do servidor de réplica: {confirmation.decode()}")

        clientSocket.close()
        print(f"Réplica do arquivo {fileName} enviada ao servidor de réplica {replica[0]}:{replica[1]}")
    except Exception as e:
        print(f"Erro ao enviar réplica do arquivo {fileName} ao servidor {replica[0]}:{replica[1]}: {e}")

# Inicializa e executa o servidor
def startServer(config, serverConfig, currentDir):
    host = serverConfig["host"]
    port = serverConfig["port"]
    middlewareHost = config["middleware"]["host"]
    middlewarePort = config["middleware"]["port"]
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind((host, port))
    serverSocket.listen(5)
    serverSocket.settimeout(1)
    
    # Recebe sinal para fechar o servidor de forma ordenada
    def signal_handler(sig, frame):
        print('Sinal de fechar a conexão recebido')
        stopEvent.set()
        serverSocket.close()
        sys.exit()
        
    signal.signal(signal.SIGINT, signal_handler)
    try:
        print(f'Servidor iniciado na porta {port}')
        while not stopEvent.is_set():
            try:
                connectionSocket, addr = serverSocket.accept()
                initial_data = connectionSocket.recv(1024)
                if initial_data == b"STATUS":
                    handle_status(connectionSocket)
                else:
                    client_thread = Thread(target=handle_client, args=(connectionSocket, addr, currentDir, middlewareHost, middlewarePort, initial_data))
                    client_thread.start()
            except timeout:
                continue
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        # Fecha o servidor e loga que está desligando
        print('Desligando servidor')
        serverSocket.close()

# Inicia servidor e busca arquivo de configuração
def main():
    currentDir = os.path.dirname(os.path.abspath(__file__))
    configPath = os.path.join(currentDir, '../../', 'config', 'config.json')
    configPath = os.path.abspath(configPath)
    with open(configPath) as configFile:
        config = json.load(configFile)

    serverDir = os.path.basename(currentDir)
    serverConf = next((s for s in config["servers"] if s["rootDir"] == serverDir), None)
    if serverConf:
        startServer(config, serverConf, currentDir)
    else:
        print(f"Configuração do servidor para o diretório {serverDir} não encontrada.")

main()
