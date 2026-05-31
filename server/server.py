from flask import Flask, request, jsonify
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from functools import wraps

app = Flask(__name__)

# Chave simétrica compartilhada (para o escopo simplificado do trabalho)
# Em produção, isso seria gerenciado via KMS ou troca de chaves Diffie-Hellman.
SHARED_KEY = b'G_F8A6oT8p_P7fXv9KxR_uUqI5mN0eA3_T1bC2yL9w8='
cipher_suite = Fernet(SHARED_KEY)

# Armazena tokens em memória: { "token": {"username": "alice", "role": "user"} }
active_sessions = {}

def get_db_connection():
    conn = sqlite3.connect('mensagens.db')
    conn.row_factory = sqlite3.Row
    return conn

# Decorator para exigir autenticação
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or token not in active_sessions:
            return jsonify({'erro': 'Acesso negado. Token inválido ou ausente.'}), 401
        return f(active_sessions[token], *args, **kwargs)
    return decorated

# Decorator para exigir papel de admin
def admin_required(f):
    @wraps(f)
    def decorated(user_session, *args, **kwargs):
        if user_session['role'] != 'admin':
            return jsonify({'erro': 'Acesso negado. Requer privilégios de administrador.'}), 403
        return f(user_session, *args, **kwargs)
    return decorated

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    senha_hash = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuarios WHERE username = ? AND password_hash = ?', (username, senha_hash)).fetchone()
    conn.close()
    
    if user:
        token = secrets.token_hex(32)
        active_sessions[token] = {'username': user['username'], 'role': user['role']}
        return jsonify({'token': token, 'role': user['role']}), 200
    
    return jsonify({'erro': 'Credenciais invalidas'}), 401

@app.route('/mensagens', methods=['POST'])
@token_required
def enviar_mensagem(user_session):
    data = request.json
    destinatario = data.get('destinatario')
    conteudo_cifrado = data.get('conteudo_cifrado').encode() # Recebe como string hex/base64, converte pra bytes
    
    conn = get_db_connection()
    # Verifica se destinatário existe
    if not conn.execute('SELECT 1 FROM usuarios WHERE username = ?', (destinatario,)).fetchone():
        return jsonify({'erro': 'Destinatario nao encontrado'}), 404

    timestamp = datetime.now(timezone.utc).isoformat()
    conn.execute('INSERT INTO mensagens (remetente, destinatario, conteudo_cifrado, timestamp, lida) VALUES (?, ?, ?, ?, ?)',
                 (user_session['username'], destinatario, conteudo_cifrado, timestamp, 0))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'Mensagem enviada e armazenada com sucesso'}), 201

@app.route('/mensagens', methods=['GET'])
@token_required
def ler_mensagens(user_session):
    conn = get_db_connection()
    
    if user_session['role'] == 'admin':
        # Admin vê todas as mensagens
        msgs = conn.execute('SELECT * FROM mensagens').fetchall()
    else:
        # Usuário comum vê apenas as que são destinadas a ele
        msgs = conn.execute('SELECT * FROM mensagens WHERE destinatario = ?', (user_session['username'],)).fetchall()
        # Marca como lidas
        conn.execute('UPDATE mensagens SET lida = 1 WHERE destinatario = ?', (user_session['username'],))
        conn.commit()
        
    conn.close()
    
    resultado = []
    for m in msgs:
        # Descriptografa a mensagem no servidor antes de enviar ao cliente
        try:
            conteudo_claro = cipher_suite.decrypt(m['conteudo_cifrado']).decode('utf-8')
        except:
            conteudo_claro = "[Erro na descriptografia]"

        resultado.append({
            'id': m['id'],
            'remetente': m['remetente'],
            'destinatario': m['destinatario'],
            'conteudo': conteudo_claro,
            'timestamp': m['timestamp'],
            'lida': m['lida']
        })
        
    return jsonify(resultado), 200

@app.route('/usuarios', methods=['POST'])
@token_required
@admin_required
def cadastrar_usuario(user_session):
    data = request.json
    novo_username = data.get('username')
    nova_senha = data.get('password')
    novo_role = data.get('role', 'user')
    
    senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)', (novo_username, senha_hash, novo_role))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'erro': 'Usuario ja existe'}), 400
    finally:
        conn.close()
        
    return jsonify({'status': 'Usuario criado'}), 201

@app.route('/usuarios/ativos', methods=['GET'])
@token_required
@admin_required
def listar_ativos(user_session):
    # Retorna os usernames com sessões ativas no momento
    ativos = list(set([session['username'] for session in active_sessions.values()]))
    return jsonify({'usuarios_ativos': ativos}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)