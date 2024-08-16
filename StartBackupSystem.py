import os
import subprocess
import time
import platform

def start_process(path, script_name):
    try:
        if platform.system() == "Linux":
            # Abre um novo terminal usando xterm e executa o script no Linux sem a opção -hold
            process = subprocess.Popen(['xterm', '-e', 'python3', script_name], cwd=path)
        elif platform.system() == "Windows":
            # Abre um novo terminal e executa o script no Windows
            process = subprocess.Popen(['start', 'cmd', '/k', f'python {script_name}'], cwd=path, shell=True)
        else:
            # Executa em segundo plano em outros sistemas
            process = subprocess.Popen(['python3', script_name], cwd=path)
        return process
    except Exception as e:
        print(f"Erro ao iniciar {script_name} em {path}: {e}")
        return None

def main():
    # Define as pastas e scripts a serem iniciados
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    client_dir = os.path.join(base_dir, 'Client')
    middleware_dir = os.path.join(base_dir, 'Middleware')
    servers_dir = os.path.join(base_dir, 'Servidores')
    
    server_dirs_and_scripts = [
        (os.path.join(servers_dir, 'Servidor1'), 'ServerOne.py'),
        (os.path.join(servers_dir, 'Servidor2'), 'ServerTwo.py'),
        (os.path.join(servers_dir, 'Servidor3'), 'ServerThree.py'),
        (os.path.join(servers_dir, 'Servidor4'), 'ServerFour.py')
    ]

    # Inicia o middleware
    print("Iniciando o Middleware...")
    middleware_process = start_process(middleware_dir, 'SimpleMiddleware.py')

    # Aguarda um pouco para garantir que o middleware esteja iniciado
    time.sleep(5)

    # Inicia os servidores
    server_processes = []
    for i, (server_dir, script_name) in enumerate(server_dirs_and_scripts, 1):
        print(f"Iniciando o Servidor {i}...")
        server_process = start_process(server_dir, script_name)
        if server_process:
            server_processes.append(server_process)

    # Aguarda um pouco para garantir que os servidores estejam iniciados
    time.sleep(5)

    # Inicia o cliente
    print("Iniciando o Cliente...")
    client_process = start_process(client_dir, 'Client.py')

    # Mantém o script rodando até que o cliente seja encerrado
    try:
        if client_process:
            client_process.wait()
    except KeyboardInterrupt:
        print("Encerrando todos os processos...")
    finally:
        # O cliente pode ser encerrado sem fechar os servidores e o middleware
        if client_process:
            client_process.terminate()

main()