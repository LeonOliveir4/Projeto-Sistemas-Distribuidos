from socket import *
from threading import Thread, Event
import json
import os
import signal
import sys
import psutil
import zlib
import select

stopEvent = Event()

# Thread que vai realizar o recebimento, decompressão e chamar o método para salvar o arquivo
def handle_client(connectionSocket, addr, rootDir, middlewareHost, middlewarePort, initialData):
    try:
        header = initialData
        while (b';comprimido;') not in header:
            headerChunk = connectionSocket.recv(1)
            if not headerChunk:
                raise IOError("Conexão fechada antes de header ser recebido")
            header += headerChunk
        headerParts = header.split(b';comprimido;')
        fileInfo = headerParts[0]
        fileData = headerParts[1] if len(headerParts) > 1 else b''
        
        try:
            fileName = fileInfo.decode().split(':')[1]
        except UnicodeDecodeError:
            print("Erro ao decodificar o header")
            connectionSocket.close()
            return
        
        isBackup = fileInfo.startswith(b'backup')
        decompressor = zlib.decompressobj()
        data = decompressor.decompress(fileData)
        while True:
            ready_to_read, _, _ = select.select([connectionSocket], [], [], 1)
            if ready_to_read:
                chunk = connectionSocket.recv(65536)
                if not chunk:
                    break
                if b"<FIM>" in chunk:
                    data += decompressor.decompress(chunk[:chunk.find(b"<FIM>")])
                    break
            else:
                break
            data += decompressor.decompress(chunk)
        data += decompressor.flush()
        print(f"Arquivo recebido e decomprimido: {fileName}")
        saveFile(fileName, data, rootDir)
        connectionSocket.send(b"Arquivo recebido e salvo com sucesso")
        # Condição para ser feito o backup somente uma vez
        if not isBackup:
            initiateBackup(fileName, data, middlewareHost, middlewarePort)
        connectionSocket.send(b"<CONFIRMADO>")
    except IOError:
        print("Fechando conexão - IOError")
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

# Envia o arquivo salvo para o Middleware escolher um servidor para salvar adicionando o prefixo de backup para evitar possivel loop
def initiateBackup(fileName, data, middlewareHost, middlewarePort):
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((middlewareHost, middlewarePort))
        header = f"backup:{fileName};comprimido;".encode()
        clientSocket.sendall(header)
        compressor = zlib.compressobj()
        compressedData = compressor.compress(data)
        if compressedData:
            clientSocket.sendall(compressedData)
        clientSocket.sendall(compressor.flush())
        clientSocket.sendall(b"<FIM>")
        clientSocket.close()
        print(f"Backup do arquivo {fileName} enviado ao middleware")
    except Exception as e:
        print(f"Erro ao enviar o backup do arquivo {fileName} ao middleware: {e}")

# Inicia o servidor
def startServer(config, serverConfig, currentDir):
    host = serverConfig["host"]
    port = serverConfig["port"]
    middlewareHost = config["middleware"]["host"]
    middlewarePort = config["middleware"]["port"]
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind((host, port))
    serverSocket.listen(5)
    serverSocket.settimeout(10)
    
    # Recebe sinal para fechar o servidor quando quiser (Ctrl + C)
    def signal_handler(sig, frame):
        print('Sinal de fechar a conexão recebido')
        stopEvent.set()
        serverSocket.close()
        sys.exit()
        
    signal.signal(signal.SIGINT, signal_handler)
    try:
        print (f'Servidor iniciado na porta {port}')
        while not stopEvent.is_set():
            try:
                connectionSocket, addr = serverSocket.accept()
                initialData = connectionSocket.recv(1024)
                if initialData == b"STATUS":
                    handle_status(connectionSocket)
                else:
                    client_thread = Thread(target=handle_client, args=(connectionSocket, addr, currentDir, middlewareHost, middlewarePort, initialData))
                    client_thread.start()
            except timeout:
                continue
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        # Fecha o servidor e loga que está desligando
        print('Desligando servidor')
        serverSocket.close()

#Inicia servidor e busca arquivo de configução
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