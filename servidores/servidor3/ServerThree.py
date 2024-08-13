from socket import *
from threading import Thread, Event, Lock
import os
import platform
import json
import zlib
import subprocess
import signal
import sys
import select

# Variável global para armazenar o número de threads em uso
activeThreads = 0
threadLock = Lock()

stopEvent = Event()

# Variável global para armazenar as informações do backup
backupServerInfo = None
backup_lock = Lock()

# Tag usada para identificar arquivos de backup
BACKUP_TAG = "_backup"

# Obter o diretório atual do script
currentDir = os.path.dirname(os.path.abspath(__file__))

# Montar o caminho completo para o arquivo de configuração
configPath = os.path.join(currentDir, 'configServerThree.json')

# Carregar configurações do sistema
with open(configPath) as configFile:
    config = json.load(configFile)

# incrementa quantidade de threads ativas
def increment_thread_count():
    global activeThreads
    with threadLock:
        activeThreads += 1
# decrementa quantidade de threads ativas
def decrement_thread_count():
    global activeThreads
    with threadLock:
        activeThreads -= 1

#coloca o addr do cliente para garantir que seu arquivo não seja sobreescrito (em versões futuras facilitaria implementar download)
def generateUniqueFilename(fileName, addr):
    clientId = f"{addr[0]}_{addr[1]}"
    uniqueFileName = f"{clientId}_{fileName}"
    return uniqueFileName

# Função para obter o uso da CPU no Windows
def getCpuUsageWindows():
    try:
        result = subprocess.run(['wmic', 'cpu', 'get', 'loadpercentage'], stdout=subprocess.PIPE)
        if result.returncode == 0:
            output = result.stdout.decode()
            # Extraindo o valor numérico do uso da CPU
            usage = int(output.strip().split('\n')[-1])
            return round(float(usage), 2)
        else:
            return "N/A"
    except Exception as e:
        print(f"Erro ao obter uso de CPU no Windows: {e}")
        return "Erro"

# Função para obter o uso da memória no Windows
def getMemUsageWindows():
    try:
        result = subprocess.run(['wmic', 'OS', 'get', 'FreePhysicalMemory,TotalVisibleMemorySize', '/Value'], stdout=subprocess.PIPE)
        if result.returncode == 0:
            output = result.stdout.decode().strip().split('\n')
            freeMemoryKb = int(output[0].split('=')[1].strip())
            totalMemoryKb = int(output[1].split('=')[1].strip())
            usedMemoryKb = totalMemoryKb - freeMemoryKb
            usage = (usedMemoryKb / totalMemoryKb) * 100
            return round(float(usage), 2)
        else:
            return "N/A"
    except Exception as e:
        print(f"Erro ao obter uso de memória no Windows: {e}")
        return "Erro"

# Função para obter o uso da CPU e Memória no Linux
def getCpuUsageLinux():
    try:
        result = subprocess.run(['grep', 'cpu ', '/proc/stat'], stdout=subprocess.PIPE)
        if result.returncode == 0:
            fields = result.stdout.decode().split()
            totalTime = sum(int(field) for field in fields[1:])
            idleTime = int(fields[4])
            usage = 100 * (1 - idleTime / totalTime)
            return round(float(usage), 2)
        else:
            return "N/A"
    except Exception as e:
        print(f"Erro ao obter uso de CPU no Linux: {e}")
        return "Erro"

def getMemUsageLinux():
    try:
        result = subprocess.run(['free', '-m'], stdout=subprocess.PIPE)
        if result.returncode == 0:
            lines = result.stdout.decode().splitlines()
            memInfo = lines[1].split()
            totalMem = int(memInfo[1])
            usedMem = int(memInfo[2])
            usage = (usedMem / totalMem) * 100
            return round(float(usage), 2)
        else:
            return "N/A"
    except Exception as e:
        print(f"Erro ao obter uso de memória no Linux: {e}")
        return "Erro"

# Função para determinar o sistema operacional e chamar as funções apropriadas
def getCpuUsage():
    if platform.system() == 'Windows':
        return getCpuUsageWindows()
    else:
        return getCpuUsageLinux()

def getMemUsage():
    if platform.system() == 'Windows':
        return getMemUsageWindows()
    else:
        return getMemUsageLinux()

# Thread que vai realizar o recebimento, descompressão e chamar o método para salvar o arquivo
def handle_client(connectionSocket, addr, rootDir, initialData):
    global backupServerInfo
    increment_thread_count()
    try:
        # Verifica se as informações recebidas são sobre o backup
        try:
            response_data = json.loads(initialData.decode(errors='ignore'))
            if "backup" in response_data:
                with backup_lock:
                    backupServerInfo = tuple(response_data["backup"])
                print(f"Informações do servidor de backup armazenadas: {backupServerInfo}")
                connectionSocket.close()
                return
        except json.JSONDecodeError as e:
            print("Seguindo por não ser backup")
            # Passa direto ignorando erro de decode caso não seja caso de backup

        # Receber e processar o cabeçalho do arquivo
        header = initialData
        while b';comprimido;' not in header:
            headerChunk = connectionSocket.recv(1)
            if not headerChunk:
                raise IOError("Conexão fechada antes de header ser recebido")
            header += headerChunk
        headerParts = header.split(b';comprimido;', 1)
        fileInfo = headerParts[0]
        fileData = headerParts[1] if len(headerParts) > 1 else b''
        
        try:
            fileName = fileInfo.decode().split(':')[1]
            is_backup = BACKUP_TAG in fileName
        except UnicodeDecodeError as e:
            print(f"Erro ao decodificar o header para o cliente {addr}: {e}")
            connectionSocket.close()
            return
        
        decompressor = zlib.decompressobj()
        data = decompressor.decompress(fileData)
        
        while True:
            readyToRead, _, _ = select.select([connectionSocket], [], [], 1)
            if readyToRead:
                try:
                    chunk = connectionSocket.recv(65536)
                    if not chunk:
                        break
                    if b"<FIM>" in chunk:
                        data += decompressor.decompress(chunk[:chunk.find(b"<FIM>")])
                        break
                    data += decompressor.decompress(chunk)
                except zlib.error as e:
                    print(f"Erro de descompressão ao lidar com o cliente {addr}: {e}")
                    break
                except Exception as e:
                    print(f"Erro inesperado ao ler dados do cliente {addr}: {e}")
                    break
            else:
                break

        data += decompressor.flush()
        print(f"Arquivo recebido e decomprimido: {fileName}")
        
        if is_backup:
            try:
                saveBackup(fileName, data, rootDir)
                print(f"Backup do arquivo {fileName} foi salvo com sucesso.")
            except Exception as e:
                print(f"Erro ao salvar o backup do arquivo {fileName}: {e}")
        else:
            # Salvar o arquivo principal
            try:
                uniqueFileName = saveFile(fileName, data, rootDir, addr)
                message = f"O arquivo {fileName} foi salvo com sucesso."
                connectionSocket.send(message.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao salvar o arquivo {fileName}: {e}")
                connectionSocket.send(b"Erro ao salvar o arquivo")

            # Enviar o arquivo para o servidor de backup
            with backup_lock:
                if backupServerInfo:
                    try:
                        sendBackup(uniqueFileName, data, backupServerInfo)
                    except Exception as e:
                        print(f"Erro ao enviar backup para o servidor {backupServerInfo}: {e}")
                else:
                    print("Nenhum servidor de backup foi definido.")
        
        connectionSocket.send(b"<CONFIRMATION>")
    except IOError as e:
        print(f"Erro de I/O ao lidar com o cliente {addr}: {e}")
    except Exception as e:
        print(f"Erro inesperado ao lidar com o cliente {addr}: {e}")
    finally:
        decrement_thread_count()
        print('Fechando conexão de thread do servidor')
        connectionSocket.close()

def saveFileInternal(fileName, fileContent, rootDir):
    try:
        filePath = os.path.join(rootDir, fileName)
        with open(filePath, "wb") as file:
            file.write(fileContent)
        print(f'O arquivo {fileName} foi salvo com sucesso.')
    except IOError as e:
        print(f"Erro de I/O ao salvar o arquivo {fileName}: {e}")
        raise
    except Exception as e:
        print(f"Erro inesperado ao salvar o arquivo {fileName}: {e}")
        raise

# Salva o arquivo principal com um nome único
def saveFile(fileName, fileContent, rootDir, addr):
    uniqueFileName = generateUniqueFilename(fileName, addr)
    saveFileInternal(uniqueFileName, fileContent, rootDir)
    return uniqueFileName  # Retorna o nome único gerado

# Salva o arquivo de backup usando o mesmo nome gerado para o arquivo principal
def saveBackup(fileName, fileContent, rootDir):
    fileName = fileName.replace(BACKUP_TAG, "")
    saveFileInternal(fileName, fileContent, rootDir)  # Não gera um novo nome, usa o mesmo nome do arquivo principal

# Pega status de uso de cpu e memória para enviar ao middleware
def getServerStatus():
    try:
        cpuUsage = getCpuUsage()
        memUsage = getMemUsage()
        return f"CPU:{cpuUsage}%, Memory:{memUsage}%, Threads:{activeThreads}"
    except Exception as e:
        print(f"Erro ao obter status do servidor: {e}")
        return "Erro ao obter status"

# Envia status de uso de cpu e memória ao middleware
def handle_status(connectionSocket):
    try:
        load_info = getServerStatus().encode()
        connectionSocket.sendall(load_info)
    except Exception as e:
        print(f"Erro ao enviar status para o middleware: {e}")
    finally:
        connectionSocket.close()

def sendBackup(fileName, data, backup):
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect(backup)
        fileNameBackup = fileName + BACKUP_TAG  # Adicionar a tag de backup ao nome do arquivo
        header = f"arquivo:{fileNameBackup};comprimido;".encode()
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
        
        confirmation = clientSocket.recv(1024)
        print(f"Confirmação recebida do servidor de backup: {confirmation.decode()}")
        clientSocket.close()
        print(f"Backup do arquivo {fileNameBackup} enviado ao servidor de backup {backup[0]}:{backup[1]}")
    except IOError as e:
        print(f"Erro de I/O ao enviar backup do arquivo {fileName} ao servidor {backup[0]}:{backup[1]}: {e}")
    except Exception as e:
        print(f"Erro inesperado ao enviar backup do arquivo {fileName} ao servidor {backup[0]}:{backup[1]}: {e}")

def startServer(config, serverConfig, currentDir):
    host = serverConfig["host"]
    port = serverConfig["port"]
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind((host, port))
    serverSocket.listen(5)
    serverSocket.settimeout(1)
    
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
                    client_thread = Thread(target=handle_client, args=(connectionSocket, addr, currentDir, initial_data))
                    client_thread.start()
            except timeout:
                continue
            except Exception as e:
                print(f"Erro ao aceitar conexão do cliente: {e}")
    except Exception as e:
        print(f"Erro no servidor: {e}")
    finally:
        print('Desligando servidor')
        serverSocket.close()

def main():
    try:
        serverDir = os.path.basename(currentDir)
        serverConf = next((s for s in config["servers"] if s["rootDir"] == serverDir), None)
        if serverConf:
            startServer(config, serverConf, currentDir)
        else:
            print(f"Configuração do servidor para o diretório {serverDir} não encontrada.")
    except FileNotFoundError as e:
        print(f"Arquivo de configuração não encontrado: {e}")
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar o arquivo de configuração: {e}")
    except Exception as e:
        print(f"Erro inesperado na inicialização do servidor: {e}")

main()