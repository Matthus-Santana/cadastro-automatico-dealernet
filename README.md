DealerNet Location Bot

Este projeto é um bot em Python feito para automatizar o cadastro de localizações no sistema DealerNet.
Ele utiliza a biblioteca PyAutoGUI para simular cliques e digitação, além de salvar o progresso em arquivos para evitar retrabalho.

---

Requisitos

Antes de rodar o projeto, você precisa ter instalado:

- Python 3.8+
- Git (para clonar o repositório)
- As bibliotecas do requirements.txt

---

Instalação

1. Clone o repositório:
   git clone https://github.com/seu-usuario/dealernet-location-bot.git
   cd dealernet-location-bot

2. Crie um ambiente virtual (opcional, mas recomendado):
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows

3. Instale as dependências:
   pip install -r requirements.txt

---

Como usar

1. Abra o DealerNet e posicione a tela de cadastro.
2. Execute o script:
   python main.py
3. O programa vai começar a cadastrar as localizações automaticamente.
   - Para parar, pressione ESC ou Ctrl+C.

---

Estrutura de arquivos

- main.py → Código principal do bot
- localizacoes_cadastradas.txt → Localizações já cadastradas
- progresso_cadastro.txt → Progresso temporário (caso precise interromper)
- requirements.txt → Dependências do projeto

---

Aviso

Este projeto é apenas para uso pessoal e testes de automação.
Cada sistema pode ter coordenadas diferentes, então pode ser necessário ajustar os valores no código da classe Config.

---

Tecnologias usadas

- Python 3
- PyAutoGUI
- Keyboard
- Logging
- tqdm

---

Próximos passos

- Melhorar a verificação de sucesso após cada cadastro
- Adicionar configuração dinâmica das coordenadas
- Criar interface gráfica simples para facilitar o uso
