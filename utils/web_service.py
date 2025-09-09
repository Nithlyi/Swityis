from flask import Flask, jsonify
import threading
import os

app = Flask(__name__)
# Declara a variável `bot` para ser acessada no contexto do módulo.
# Ela será definida pela função `run_web_service`.
global_bot = None 

# NOVA ROTA: Responde a requisições na URL raiz para o Uptime Robot
@app.route('/', methods=['GET', 'HEAD'])
def home():
    """Retorna um status 200 OK para o Uptime Robot."""
    return 'Serviço está online!', 200

# Endpoint de exemplo para o web service
@app.route('/status', methods=['GET'])
def get_status():
    """Retorna o status atual do bot."""
    if global_bot and global_bot.is_ready():
        return jsonify({"status": "Online", "latency": f"{global_bot.latency:.2f} ms"})
    else:
        return jsonify({"status": "Offline"})

def run_web_service(bot_instance):
    """Inicia o servidor Flask em uma nova thread."""
    global global_bot # Usa a variável global
    global_bot = bot_instance
    port = os.getenv('PORT', 5000)
    try:
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False), daemon=True).start()
        print(f"Web service rodando na porta {port}.")
    except Exception as e:
        print(f"Erro ao iniciar o web service: {e}")
