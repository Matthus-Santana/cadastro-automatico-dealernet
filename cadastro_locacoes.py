import pyautogui
import time
import keyboard
from pathlib import Path
import logging
from shutil import copyfile
import threading
import signal
import sys
import os

# Importa bibliotecas opcionais com verificação de disponibilidade
try:
    from tqdm import tqdm
except ImportError:
    # Define tqdm como uma função de identidade caso não esteja instalado
    tqdm = lambda x, **kwargs: x

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False
    logging.warning("pygetwindow não instalado. Verificação de foco será desativada.")

# Configura o logging para exibir mensagens com timestamp e nível
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Classe para organizar configurações do script
class Config:
    """Centraliza configurações fixas do sistema para fácil manutenção."""
    ARQUIVO_LOCALIZACOES = "localizacoes_cadastradas.txt"  # Arquivo para armazenar localizações
    ARQUIVO_PROGRESSO = "progresso_cadastro.txt"  # Arquivo para salvar progresso
    COORD_BOTAO_ADICIONAR = (267, 224)  # Coordenadas do botão de adicionar
    COORD_CAMPO_LOCALIZACAO = (216, 222)  # Coordenadas do campo de localização
    COORD_BOTAO_CONFIRMAR = (488, 359)  # Coordenadas do botão de confirmar
    PAUSA_ENTRE_ACOES = 0.1  # Pausa entre ações para estabilidade
    TEMPO_AGUARDA_FORM = 0.2  # Tempo de espera para formulário
    TEMPO_AGUARDA_CONFIRMAR = 0.5  # Tempo de espera para confirmação
    TEMPO_ESTABILIZAR = 0.1  # Tempo para estabilizar ações
    SUCESSO_TIMEOUT = 0.3  # Timeout para verificar sucesso
    MAX_ATTEMPTS = 3  # Máximo de tentativas para cadastro
    SALVAR_A_CADA = 10  # Frequência de salvamento do progresso
    PREFIXO = "FA01"  # Prefixo para códigos de localização
    LETRAS_PRATELEIRAS = ['A', 'B', 'C', 'D', 'E', 'F']  # Letras usadas nas prateleiras
    SUB_NUM_RANGE = range(1, 11)  # Intervalo de números para sub-localizações
    IMPARES_RANGE = range(1, 30, 2)  # Números ímpares para localizações
    PARES_RANGE = range(2, 20, 2)  # Números pares para localizações

# Configurações do PyAutoGUI para segurança e pausa padrão
pyautogui.FAILSAFE = True  # Ativa o fail-safe para interromper com movimento rápido do mouse
pyautogui.PAUSE = 0.1  # Pausa padrão entre ações do PyAutoGUI

# Variáveis globais para controle do script
stop_event = threading.Event()  # Evento para sinalizar interrupção
cadastradas_set = None  # Conjunto global para localizações cadastradas

def signal_handler(sig, frame):
    """Interrompe o script ao receber sinal de Ctrl+C."""
    logging.info("Interrupção detectada via Ctrl+C.")
    stop_event.set()
    sys.exit(0)

def monitor_interruption():
    """Monitora a tecla ESC para interromper o script."""
    while not stop_event.is_set():
        if keyboard.is_pressed('esc'):
            stop_event.set()
            logging.info("Interrupção detectada pela tecla ESC.")
            break
        time.sleep(0.05)  # Pequena pausa para evitar uso excessivo de CPU

def validate_coordinates(coord):
    """Valida se as coordenadas estão dentro dos limites da tela."""
    screen_width, screen_height = pyautogui.size()
    x, y = coord
    if not (0 <= x < screen_width and 0 <= y < screen_height):
        raise ValueError(f"Coordenadas {coord} estão fora dos limites da tela ({screen_width}x{screen_height})")

def normalize(loc):
    """Normaliza uma string de localização para comparação consistente."""
    return ' '.join(loc.strip().upper().split())

def carregar_localizacoes_cadastradas():
    """Carrega localizações já cadastradas do arquivo."""
    try:
        arquivo = Path(Config.ARQUIVO_LOCALIZACOES)
        if arquivo.exists() and arquivo.stat().st_size > 0:
            with open(Config.ARQUIVO_LOCALIZACOES, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                normalized_set = {normalize(l) for l in lines}
                logging.info(f"Carregadas {len(normalized_set)} localizações do arquivo.")
                return normalized_set, lines
        logging.info("Arquivo de localizações vazio ou inexistente. Iniciando com conjunto vazio.")
        return set(), []
    except IOError as e:
        logging.error(f"Erro ao carregar localizações: {e}")
        return set(), []

def salvar_localizacao(localizacao, cadastradas_set):
    """Salva uma nova localização no arquivo, se ainda não estiver cadastrada."""
    try:
        localizacao_normalizada = normalize(localizacao)
        if localizacao_normalizada in cadastradas_set:
            logging.warning(f"Localização '{localizacao}' já está cadastrada. Pulando salvamento.")
            return
        with open(Config.ARQUIVO_LOCALIZACOES, 'a') as f:
            f.write(f"{localizacao}\n")
        cadastradas_set.add(localizacao_normalizada)
        logging.info(f"Localização '{localizacao}' salva no arquivo.")
    except IOError as e:
        logging.error(f"Erro ao salvar localização {localizacao}: {e}")

def salvar_progresso(localizacoes_cadastradas):
    """Salva o progresso das localizações cadastradas no arquivo de progresso."""
    try:
        with open(Config.ARQUIVO_PROGRESSO, 'w') as f:
            for loc in localizacoes_cadastradas:
                f.write(f"{loc}\n")
        logging.info("Progresso salvo.")
    except IOError as e:
        logging.error(f"Erro ao salvar progresso: {e}")

def carregar_progresso():
    """Carrega o progresso salvo do arquivo de progresso."""
    try:
        arquivo = Path(Config.ARQUIVO_PROGRESSO)
        if arquivo.exists():
            with open(Config.ARQUIVO_PROGRESSO, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        return []
    except IOError as e:
        logging.error(f"Erro ao carregar progresso: {e}")
        return []

def verificar_sucesso():
    """Verifica se a operação de cadastro foi bem-sucedida."""
    logging.info("Verificando sucesso da operação.")
    time.sleep(Config.SUCESSO_TIMEOUT)
    # TODO: Adicionar verificação robusta, como captura de tela ou validação do campo
    logging.info("Sucesso assumido após espera.")
    return True

def detectar_foco():
    """Verifica se a janela DealerNet está em foco."""
    if not PYGETWINDOW_AVAILABLE:
        logging.info("Verificação de foco desativada (pygetwindow não instalado).")
        return True
    try:
        active_window = gw.getActiveWindow()
        if active_window and "DealerNet" in active_window.title:
            return True
        logging.warning("DealerNet não está em foco. Tentando trazer para frente...")
        for win in gw.getAllTitles():
            if "DealerNet" in win:
                gw.getWindowsWithTitle(win)[0].activate()
                time.sleep(0.2)
                return True
        logging.error("Janela DealerNet não encontrada.")
        return False
    except Exception as e:
        logging.error(f"Erro ao verificar foco: {e}")
        return False

def click_botao_adicionar():
    """Clica no botão de adicionar no formulário."""
    logging.info("Clicando no botão adicionar.")
    pyautogui.click(*Config.COORD_BOTAO_ADICIONAR)
    time.sleep(Config.PAUSA_ENTRE_ACOES)

def preencher_campo_localizacao(localizacao):
    """Preenche o campo de localização com o valor fornecido."""
    start_time = time.time()
    logging.info(f"Preenchendo campo com localização: {localizacao}")
    pyautogui.click(*Config.COORD_CAMPO_LOCALIZACAO)
    time.sleep(Config.TEMPO_AGUARDA_FORM)
    
    # Limpa o campo antes de preencher
    pyautogui.hotkey('ctrl', 'a')  # Selecionar tudo
    time.sleep(Config.TEMPO_ESTABILIZAR)
    pyautogui.press('delete')  # Apagar
    time.sleep(Config.TEMPO_ESTABILIZAR)
    
    # Digita a localização
    pyautogui.typewrite(localizacao)
    time.sleep(Config.TEMPO_ESTABILIZAR * 2)
    
    # Move o mouse para evitar interferência
    pyautogui.moveTo(*Config.COORD_BOTAO_ADICIONAR)
    logging.info(f"Campo preenchido e mouse movido para botão adicionar. Tempo: {time.time() - start_time:.2f}s")

def click_confirmar():
    """Clica no botão de confirmar no formulário."""
    logging.info("Clicando no botão confirmar.")
    pyautogui.click(*Config.COORD_BOTAO_CONFIRMAR)
    time.sleep(Config.TEMPO_AGUARDA_CONFIRMAR)

def mover_para_botao_adicionar():
    """Move o mouse para o botão de adicionar."""
    logging.info("Movendo mouse para botão adicionar.")
    pyautogui.moveTo(*Config.COORD_BOTAO_ADICIONAR)

def log_erro_com_screenshot(localizacao, e):
    """Registra erro com captura de tela para depuração."""
    screenshot_path = f"erro_{localizacao.replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.png"
    pyautogui.screenshot(screenshot_path)
    logging.error(f"Erro ao cadastrar {localizacao}: {e}. Screenshot salvo em {screenshot_path}")

def cadastrar_localizacao(localizacao, cadastradas_set):
    """Tenta cadastrar uma localização no sistema."""
    start_time = time.time()
    try:
        if stop_event.is_set():
            raise KeyboardInterrupt("Interrompido pelo usuário")
        localizacao_normalizada = normalize(localizacao)
        if localizacao_normalizada in cadastradas_set:
            logging.info(f"Localização '{localizacao}' já cadastrada. Pulando cadastro.")
            return False
        if not detectar_foco():
            raise RuntimeError("DealerNet não está em foco.")
        
        # Limpa o campo antes de qualquer ação
        pyautogui.click(*Config.COORD_CAMPO_LOCALIZACAO)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        time.sleep(Config.TEMPO_ESTABILIZAR)

        click_botao_adicionar()
        preencher_campo_localizacao(localizacao)
        click_confirmar()
        if verificar_sucesso():
            logging.info(f"Sucesso detectado para {localizacao}")
            salvar_localizacao(localizacao, cadastradas_set)
            logging.info(f"Localização '{localizacao}' cadastrada com sucesso. Tempo: {time.time() - start_time:.2f}s")
            mover_para_botao_adicionar()
            return True
        else:
            logging.warning(f"Sucesso não detectado para {localizacao}. Verificando se já está cadastrada.")
            salvar_localizacao(localizacao, cadastradas_set)  # Marca como cadastrada
            mover_para_botao_adicionar()
            return False
    except (pyautogui.FailSafeException, KeyboardInterrupt, RuntimeError) as e:
        log_erro_com_screenshot(localizacao, e)
        mover_para_botao_adicionar()
        return False
    except Exception as e:
        log_erro_com_screenshot(localizacao, e)
        # Marca como cadastrada se o erro indicar duplicidade
        if "já cadastrada" in str(e).lower() or "duplicada" in str(e).lower():
            salvar_localizacao(localizacao, cadastradas_set)
        mover_para_botao_adicionar()
        return False

def cadastrar_com_retry(localizacao, cadastradas_set, max_attempts=Config.MAX_ATTEMPTS):
    """Tenta cadastrar uma localização com retries em caso de falha."""
    localizacao_normalizada = normalize(localizacao)
    if localizacao_normalizada in cadastradas_set:
        logging.info(f"Localização '{localizacao}' já cadastrada. Ignorando tentativas.")
        return False
    for attempt in range(max_attempts):
        if stop_event.is_set():
            return False
        if cadastrar_localizacao(localizacao, cadastradas_set):
            return True
        logging.info(f"Tentativa {attempt + 1} falhou. Backoff...")
        time.sleep(0.1 * (attempt + 1))  # Aumenta espera em cada tentativa
    logging.error(f"Falha após {max_attempts} tentativas para {localizacao}. Marcando como cadastrada.")
    salvar_localizacao(localizacao, cadastradas_set)
    return False

def gerar_localizacoes():
    """Gera todas as localizações possíveis com base nas configurações."""
    localizacoes = []
    for num in Config.IMPARES_RANGE:
        for letra in Config.LETRAS_PRATELEIRAS:
            for sub_num in Config.SUB_NUM_RANGE:
                cod = f"{Config.PREFIXO} {num:02d} {letra}{sub_num:02d}"
                localizacoes.append(cod)
    for num in Config.PARES_RANGE:
        for letra in Config.LETRAS_PRATELEIRAS:
            for sub_num in Config.SUB_NUM_RANGE:
                cod = f"{Config.PREFIXO} {num:02d} {letra}{sub_num:02d}"
                localizacoes.append(cod)
    return localizacoes

def main():
    """Função principal que coordena o processo de cadastro de localizações."""
    global cadastradas_set
    signal.signal(signal.SIGINT, signal_handler)  # Configura handler para Ctrl+C
    try:
        # Valida coordenadas antes de iniciar
        validate_coordinates(Config.COORD_BOTAO_ADICIONAR)
        validate_coordinates(Config.COORD_CAMPO_LOCALIZACAO)
        validate_coordinates(Config.COORD_BOTAO_CONFIRMAR)
    except ValueError as e:
        logging.error(f"Validação de coordenadas falhou: {e}")
        return
    # Cria backup do arquivo de localizações, se existir
    arquivo = Path(Config.ARQUIVO_LOCALIZACOES)
    if arquivo.exists():
        try:
            copyfile(Config.ARQUIVO_LOCALIZACOES, f"{Config.ARQUIVO_LOCALIZACOES}.bak")
            logging.info("Backup do arquivo de localizações criado.")
        except IOError as e:
            logging.error(f"Erro ao criar backup: {e}")
    # Carrega localizações e progresso
    cadastradas_set, _ = carregar_localizacoes_cadastradas()
    logging.info(f"Localizações já cadastradas encontradas: {len(cadastradas_set)}")
    todas_localizacoes = gerar_localizacoes()
    progress_local = carregar_progresso()
    progress_set = {normalize(loc) for loc in progress_local}
    localizacoes_para_cadastrar = [loc for loc in todas_localizacoes 
                                   if normalize(loc) not in cadastradas_set and normalize(loc) not in progress_set]
    logging.info(f"Total de localizações a cadastrar: {len(localizacoes_para_cadastrar)}")
    if not localizacoes_para_cadastrar:
        logging.info("Nenhuma nova localização para cadastrar.")
        return
    # Informa início do processo
    logging.info("O script começará em 5 segundos. Posicione a tela do DealerNet. Pressione ESC ou Ctrl+C para interromper.")
    logging.info("Usando coordenadas fixas.")
    time.sleep(5)
    # Inicia thread para monitorar ESC
    esc_thread = threading.Thread(target=monitor_interruption, daemon=True)
    esc_thread.start()
    cadastradas_neste_run = []
    # Usa barra de progresso para acompanhar o cadastro
    with tqdm(total=len(localizacoes_para_cadastrar), desc="Cadastrando localizações", unit="loc") as pbar:
        for index, local in enumerate(localizacoes_para_cadastrar):
            if stop_event.is_set():
                logging.info("Execução interrompida pelo usuário.")
                break
            logging.info(f"Cadastrando {index + 1}/{len(localizacoes_para_cadastrar)}: {local}")
            if cadastrar_com_retry(local, cadastradas_set):
                cadastradas_neste_run.append(local)
                if len(cadastradas_neste_run) % Config.SALVAR_A_CADA == 0:
                    salvar_progresso(cadastradas_neste_run)
            pbar.update(1)
    salvar_progresso(cadastradas_neste_run)
    esc_thread.join()
    logging.info("Processo concluído!")
    # Remove arquivo de progresso se não foi interrompido
    if not stop_event.is_set() and Path(Config.ARQUIVO_PROGRESSO).exists():
        os.remove(Config.ARQUIVO_PROGRESSO)

if __name__ == "__main__":
    main()