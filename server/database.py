import sqlite3
import hashlib

def init_db():
    conn = sqlite3.connect('mensagens.db')
    cursor = conn.cursor()

    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            role TEXT
        )
    ''')

    # Tabela de Mensagens
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remetente TEXT,
            destinatario TEXT,
            conteudo_cifrado BLOB,
            timestamp TEXT,
            lida INTEGER
        )
    ''')

    # Inserir usuários de teste (senha igual ao login para facilitar o teste)
    users = [
        ('admin', hashlib.sha256(b'admin').hexdigest(), 'admin'),
        ('alice', hashlib.sha256(b'alice').hexdigest(), 'user'),
        ('bob', hashlib.sha256(b'bob').hexdigest(), 'user')
    ]
    
    for u in users:
        try:
            cursor.execute('INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)', u)
        except sqlite3.IntegrityError:
            pass # Usuário já existe

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Banco de dados inicializado com sucesso.")