import requests
import json
from cryptography.fernet import Fernet

BASE_URL = 'http://127.0.0.1:5000'
SHARED_KEY = b'G_F8A6oT8p_P7fXv9KxR_uUqI5mN0eA3_T1bC2yL9w8='
cipher_suite = Fernet(SHARED_KEY)

class ClienteSD:
    def __init__(self):
        self.token = None
        self.username = None
        self.role = None

    def login(self):
        print("\n--- LOGIN ---")
        user = input("Username: ")
        pwd = input("Senha: ")
        
        resp = requests.post(f"{BASE_URL}/login", json={'username': user, 'password': pwd})
        
        if resp.status_code == 200:
            data = resp.json()
            self.token = data['token']
            self.role = data['role']
            self.username = user
            print(f"Login de {user} efetuado com sucesso! Token gerado.")
        else:
            print(f"Erro: {resp.json().get('erro')}")

    def get_headers(self):
        return {'Authorization': self.token, 'Content-Type': 'application/json'}

    def enviar_mensagem(self):
        print("\n--- ENVIAR MENSAGEM ---")
        destinatario = input("Para quem (username): ")
        mensagem = input("Digite a mensagem: ")
        
        # O Cliente A criptografa ANTES de enviar para a rede
        msg_cifrada = cipher_suite.encrypt(mensagem.encode()).decode()
        
        payload = {'destinatario': destinatario, 'conteudo_cifrado': msg_cifrada}
        resp = requests.post(f"{BASE_URL}/mensagens", headers=self.get_headers(), json=payload)
        print(resp.json().get('status', resp.json().get('erro')))

    def ler_mensagens(self):
        print("\n--- CAIXA DE MENSAGENS ---")
        resp = requests.get(f"{BASE_URL}/mensagens", headers=self.get_headers())
        if resp.status_code == 200:
            msgs = resp.json()
            if not msgs:
                print("Nenhuma mensagem encontrada.")
            for m in msgs:
                status = "Lida" if m['lida'] == 1 else "Nova"
                print(f"[{m['timestamp']}] De: {m['remetente']} Para: {m['destinatario']} | Status: {status}")
                print(f"   Conteúdo (já em texto claro): {m['conteudo']}")
        else:
            print(f"Erro: {resp.json().get('erro')}")

    def menu_admin(self):
        print("\n--- MENU ADMIN ---")
        print("1 - Cadastrar novo usuário")
        print("2 - Ver usuários ativos")
        opc = input("Escolha: ")
        
        if opc == '1':
            n_user = input("Novo username: ")
            n_pwd = input("Nova senha: ")
            resp = requests.post(f"{BASE_URL}/usuarios", headers=self.get_headers(), 
                                 json={'username': n_user, 'password': n_pwd, 'role': 'user'})
            print(resp.json())
        elif opc == '2':
            resp = requests.get(f"{BASE_URL}/usuarios/ativos", headers=self.get_headers())
            print(resp.json())

    def menu_principal(self):
        while True:
            if not self.token:
                self.login()
                if not self.token: continue
            
            print(f"\n[ Logado como: {self.username} | Nível: {self.role} ]")
            print("1. Enviar Mensagem")
            print("2. Ler Minhas Mensagens (ou todas se Admin)")
            if self.role == 'admin':
                print("3. Menu Admin")
            print("0. Sair")
            
            op = input("Escolha: ")
            if op == '1': self.enviar_mensagem()
            elif op == '2': self.ler_mensagens()
            elif op == '3' and self.role == 'admin': self.menu_admin()
            elif op == '0': break
            else: print("Opção inválida.")

if __name__ == '__main__':
    cli = ClienteSD()
    cli.menu_principal()