import os
import json
from socket import *
import zlib

def send_file(fileName, middlewareHost, middlewarePort):
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((middlewareHost, middlewarePort))
        clientSocket.sendall(b"GET_SERVERS")
        
        response = clientSocket.recv(1024)
        server_info = json.loads(response.decode())
        primary = tuple(server_info["primary"])
        clientSocket.close()
        
        # Enviar arquivo para o servidor primário
        with open(fileName, 'rb') as f:
            primarySocket = socket(AF_INET, SOCK_STREAM)
            primarySocket.connect(primary)
            header = f"arquivo:{fileName};comprimido;".encode()
            primarySocket.sendall(header)
            compressor = zlib.compressobj()
            while chunk := f.read(65536):
                compressedChunk = compressor.compress(chunk)
                if compressedChunk:
                    primarySocket.sendall(compressedChunk)
            primarySocket.sendall(compressor.flush())
            primarySocket.sendall(b"<FIM>")
            confirmation = primarySocket.recv(1024)
            print(confirmation.decode())
            primarySocket.close()

    except FileNotFoundError:
        print(f"Arquivo {fileName} não encontrado.")
    except ConnectionRefusedError:
        print(f"Não foi possível conectar ao middleware em {middlewareHost}:{middlewarePort} para transferir o arquivo {fileName}.")
    except Exception as e:
        print(f"Erro ao enviar o arquivo {fileName}: {e}")

# Exibir menu do cliente
def client_menu():
    # Carregar configuração do cliente
    with open('clientConfig.json') as config_file:
        config = json.load(config_file)
    
    middlewareHost = config['middleware']['host']
    middlewarePort = config['middleware']['port']
    while True:
        print("\nMenu:")
        print("1. Backup de arquivo")
        print("2. Sair")
        choice = input("Escolha uma opção: ")
        if choice == "1":
            fileName = input("Digite o nome do arquivo: ")
            if os.path.exists(fileName):
                send_file(fileName, middlewareHost, middlewarePort)
            else:
                print("Arquivo não encontrado.")
        elif choice == "2":
            break
        else:
            print("Opção inválida.")

client_menu()