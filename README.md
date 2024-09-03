# Projeto-Sistemas-Distribuidos
Projeto da Disciplina de Sistemas Distribuídos - UFABC - Sistema distribuído responsável por realizar backups de arquivos com suporte a replicação de conteúdo

 3.1. Critérios de Seleção\**
 A seleção dos servidores primário e de backup é feita da seguinte forma, tem um método
 que pega status de cpu, memória e threads ativas do servidor, então são comparados por
 ordem de importância inicialmente carga de cpu e se der empate, carga de memória,
 caso os valores sejam muito próximos, tem uma pequena margem de erro, que chamei
 de “withinMargin” a qual se estiver na margem, irá selecionar os arquivos com menos
 threads ativas. Vale lembrar que também adicionei um caso de servidores validos apenas,
 ou seja, se tentar buscar o status, e der erro por algum motivo (muitas vezes ocorre no
 Windows- sim o método funciona tanto para Windows quanto linux) ele não adiciona
 esse servidor na lista de servidores válidos selecionávels, mas caso menos de 2 servidores
 válidos estejam na lista, então é chamada novamente a função de buscar o status.

Instruções de Execução:\**
Necessário ter o python (python 3) disponível no Windows ou no Ubuntu, cmd no Windows e xterm no Ubuntu, e algumas libs as quais já serão importadas ao projeto quando clonar como `socket, Thread, Event, Lock, os, json, signal, sys, random, zlib, select, sys, signal, subprocess e platorm, time`.
 1. **Atualize a lista de pacotes**:
 `sudo apt-get update`
 2. **Instale o xterm:
 `sudo apt-get install xterm`
 3. **Verifique a instalação**:
 Execute o comando abaixo para abrir uma nova janela de xterm e verificar se a instalação foi bem-sucedida:
 `xterm`
 Se a janela abrir corretamente, a instalação está concluída.
 4. **Uso do xterm:
 Para executar um script Python em uma nova janela do xterm, utilize o seguinte
 comando:
 `python3 StartBackupSystem.py`
 O terminal xterm permanecerá aberto após a execução do script. Caso tenha algum erro, pode também executar um arquivo por vez ou executar via weblogic.
 No caso de Windows, basta rodar no cmd
 `python StartBackupSystem.py`
