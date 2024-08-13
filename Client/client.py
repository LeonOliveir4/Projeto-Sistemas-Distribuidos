from socket import *
from threading import Thread, Lock, Event
import os
import json
import zlib
import time

# Dicionário para armazenar o status das transferências
transferStatus = {}
transferLock = Lock()
exitEvent = Event()

# Função para limpar a tela
def clearScreen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Função para exibir o menu
def showMenu():
    print("=" * 50)
    print(" " * 15 + "Menu de Backup")
    print("=" * 50)
    print("1. Backup de arquivo")
    print("2. Listar arquivos disponíveis")
    print("3. Status das transferências")
    print("4. Limpar")
    print("5. Sair")
    print("=" * 50)

# Função para enviar um arquivo
def send_file(filePath, fileName, middlewareHost, middlewarePort, identifier):
    try:
        if exitEvent.is_set():
            return
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((middlewareHost, middlewarePort))
        clientSocket.sendall(b"GET_SERVERS")
        
        response = clientSocket.recv(1024)
        serverInfo = json.loads(response.decode())
        primary = tuple(serverInfo["primary"])
        clientSocket.close()
        
        fileSize = os.path.getsize(filePath)
        bytesSent = 0
        
        # Enviar arquivo para o servidor primário
        with open(filePath, 'rb') as f:
            primarySocket = socket(AF_INET, SOCK_STREAM)
            primarySocket.connect(primary)
            header = f"arquivo:{fileName};comprimido;".encode()
            primarySocket.sendall(header)
            compressor = zlib.compressobj()
            while chunk := f.read(65536):
                if exitEvent.is_set():
                    primarySocket.close()
                    return
                compressedChunk = compressor.compress(chunk)
                if compressedChunk:
                    primarySocket.sendall(compressedChunk)
                    bytesSent += len(compressedChunk)
                    with transferLock:
                        progress = (bytesSent / fileSize) * 100
                        transferStatus[identifier] = f"Transferindo... {progress:.2f}%"
            primarySocket.sendall(compressor.flush())
            primarySocket.sendall(b"<FIM>")
            confirmation = primarySocket.recv(1024)
            primarySocket.close()

        with transferLock:
            transferStatus[identifier] = "Salvo"

        clearScreen()
        print(confirmation.decode())
        if not exitEvent.is_set():
            showMenu()

    except FileNotFoundError:
        clearScreen()
        print(f"Arquivo {fileName} não encontrado.")
        with transferLock:
            transferStatus[identifier] = "Erro: Arquivo não encontrado"
        if not exitEvent.is_set():
            showMenu()
    except ConnectionRefusedError:
        clearScreen()
        print(f"Não foi possível conectar ao servidor de backup para transferir o arquivo {fileName}. Tente novamente mais tarde")
        with transferLock:
            transferStatus[identifier] = "Erro: Conexão recusada"
        if not exitEvent.is_set():
            showMenu()
    except Exception as e:
        clearScreen()
        print(f"Erro ao enviar o arquivo {fileName}: {e}")
        with transferLock:
            transferStatus[identifier] = f"Erro: {e}"
        if not exitEvent.is_set():
            showMenu()
    finally:
        with transferLock:
            if identifier in transferStatus and transferStatus[identifier] == "Salvando...":
                transferStatus[identifier] = "Erro: Falha desconhecida"
        # Exibir o menu novamente após o término da operação
        if not exitEvent.is_set():
            print("\nEscolha uma opção: ", end="")

# Função para listar os arquivos disponíveis
def listFiles(currentDir):
    files = [f for f in os.listdir(currentDir) if os.path.isfile(os.path.join(currentDir, f))]
    print("=" * 50)
    if files:
        print("\nArquivos disponíveis: ")
        for file in files:
            print(f"- {file}")
    else:
        print("Nenhum arquivo disponível.")
    print("=" * 50)

# Função para exibir o status das transferências
def showTransferStatus():
    print("=" * 50)
    print(" " * 15 + "Status das Transferências Durante ESSA Operação")
    print("=" * 50)
    with transferLock:
        if transferStatus:
            print("\nStatus das transferências:")
            for identifier, status in transferStatus.items():
                print(f"- {identifier} status: {status}")
        else:
            print("Nenhuma transferência em andamento.")
    print("=" * 50)

# Função para verificar se há transferências em andamento
def hasActiveTransfers():
    with transferLock:
        return any(status.startswith("Transferindo") | status.startswith("Iniciando") for status in transferStatus.values())

# Exibir menu do cliente
def client_menu():
    # Obter o diretório atual do script
    currentDir = os.path.dirname(os.path.abspath(__file__))

    # Montar o caminho completo para o arquivo de configuração
    configPath = os.path.join(currentDir, 'clientConfig.json')

    # Carregar configurações do sistema
    with open(configPath) as configFile:
        config = json.load(configFile)
    
    middlewareHost = config['middleware']['host']
    middlewarePort = config['middleware']['port']

    while True:
        showMenu()
        choice = input("Escolha uma opção: ").strip()  # Captura a escolha do usuário
        
        if choice == "1":
            fileName = input("Digite o nome do arquivo mais junto de sua extensão: ")
            filePath = os.path.join(currentDir, fileName)
            if os.path.exists(filePath):
                identifier = f'{fileName} transferencia iniciada no horario : {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}'  # Cria um identificador único para cada envio
                with transferLock:
                    transferStatus[identifier] = "Iniciando processo de backup..."
                transfer_thread = Thread(target=send_file, args=(filePath, fileName, middlewareHost, middlewarePort, identifier))
                transfer_thread.start()
            else:
                print("Arquivo não encontrado.")
        
        elif choice == "2":
            listFiles(currentDir)
        
        elif choice == "3":
            showTransferStatus()
        
        elif choice == "4":
            clearScreen()
        elif choice == "5":
            if hasActiveTransfers():
                print("Existem transferências em andamento. Deseja realmente sair?")
                confirm = input("Digite 'sair' para confirmar ou pressione Enter para cancelar: ").strip().lower()
                if confirm == "sair":
                    exitEvent.set()  # Sinaliza para todas as threads que é hora de sair
                    print("=" * 50)
                    print("Saindo do sistema...")
                    print("=" * 50)
                    break
            else:
                print("=" * 50)
                print("Saindo do sistema...")
                print("=" * 50)
                break
        else:
            print("Opção inválida.")

client_menu()