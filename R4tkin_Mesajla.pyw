import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext
import time

PORT = 5555
DISCOVERY_PORT = 5556
ROOM_NAME = "R4tkin_MesajlaRoom"

clients = []
names = []
admin_name = None
client = None
username = ""

# ================= SERVER =================
def start_server():
    global clients, names, admin_name
    clients = []
    names = []
    admin_name = None

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("0.0.0.0", PORT))
        server.listen()
    except:
        add_message("❌ Port kullanılıyor, sunucu açılamadı")
        return

    threading.Thread(target=discovery_server, daemon=True).start()
    add_message("💻 Sunucu başlatıldı. LAN üzerinden bağlanabilirsiniz.")

    while True:
        try:
            c, addr = server.accept()
            c.send("NAME".encode())
            name = c.recv(1024).decode()

            if name in names:
                c.send("NAME_TAKEN".encode())
                c.close()
                continue

            clients.append(c)
            names.append(name)
            if admin_name is None:
                admin_name = name

            send_user_list()
            broadcast(f"🔔 {name} katıldı")
            threading.Thread(target=handle_client, args=(c,), daemon=True).start()
        except:
            break

def handle_client(c):
    while True:
        try:
            msg = c.recv(1024)
            if not msg: break
            broadcast(msg.decode())
        except:
            break
    remove_client(c)

def remove_client(c):
    if c in clients:
        i = clients.index(c)
        name = names[i]
        clients.remove(c)
        names.remove(name)
        broadcast(f"❌ {name} ayrıldı")
        send_user_list()

def broadcast(msg):
    for c in clients:
        try:
            c.send(msg.encode())
        except:
            pass

def send_user_list():
    data = "USERS:" + ",".join(names)
    for c in clients:
        try:
            c.send(data.encode())
        except:
            pass

# ================= DISCOVERY =================
def discovery_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", DISCOVERY_PORT))
    while True:
        try:
            data, addr = s.recvfrom(1024)
            if data == b"DISCOVER":
                s.sendto(f"ROOM:{ROOM_NAME}".encode(), addr)
        except:
            break

def discover_server(timeout=2):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)
    try:
        s.sendto(b"DISCOVER", ("255.255.255.255", DISCOVERY_PORT))
        data, addr = s.recvfrom(1024)
        if data.decode().startswith("ROOM:"):
            return addr[0]
    except:
        return None
    return None

# ================= CLIENT =================
def start_client(ip):
    global client
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((ip, PORT))
    except:
        add_message("❌ Sunucuya bağlanılamadı.")
        return

    def receive():
        while True:
            try:
                msg = client.recv(1024).decode()
                if not msg:
                    break
                if msg == "NAME":
                    client.send(username.encode())
                elif msg.startswith("USERS:"):
                    users = msg.replace("USERS:", "").split(",")
                    root.after(0, update_users, users)
                elif msg == "NAME_TAKEN":
                    add_message("❌ Bu isim alınmış!")
                else:
                    add_message(msg)
            except:
                break
    threading.Thread(target=receive, daemon=True).start()

def send_message(event=None):
    msg = entry.get().strip()
    if msg and client:
        try:
            client.send(f"{username}: {msg}".encode())
            entry.delete(0, tk.END)
        except:
            add_message("❌ Mesaj gönderilemedi.")

# ================= GUI =================
def add_message(msg):
    chat.config(state="normal")
    chat.insert(tk.END, msg + "\n")
    chat.config(state="disabled")
    chat.yview(tk.END)

def update_users(lst):
    user_list.delete(0, tk.END)
    for u in lst:
        if u:
            user_list.insert(tk.END, u)

def start_app():
    global username
    username = simpledialog.askstring("Ad", "Adın:", parent=root)
    if username:
        threading.Thread(target=check_or_create_server, daemon=True).start()
        start_chat()

def check_or_create_server():
    ip = discover_server()
    if ip:
        add_message(f"🌐 Sunucu bulundu: {ip}, bağlanıyor...")
        start_client(ip)
    else:
        add_message("🌐 Sunucu bulunamadı, kendi sunucunuzu oluşturuyorsunuz...")
        threading.Thread(target=start_server, daemon=True).start()
        time.sleep(0.5)  # Server thread başlasın
        start_client("127.0.0.1")

def start_chat():
    start_frame.pack_forget()
    chat_frame.pack(fill="both", expand=True)
    entry_frame.pack(fill="x")

# ================= UI =================
root = tk.Tk()
root.title("R4tkin_Mesajla")
root.geometry("600x500")
root.configure(bg="#1e1e1e")

start_frame = tk.Frame(root, bg="#1e1e1e")
start_frame.pack(expand=True)
tk.Label(start_frame, text="R4tkin_Mesajla", fg="white", bg="#1e1e1e",
         font=("Arial", 25, "bold")).pack(pady=20)
tk.Button(start_frame, text="Sohbete Başla", command=start_app,
          bg="#444", fg="white", font=("Arial", 12), width=20).pack(pady=10)

chat_frame = tk.Frame(root, bg="#1e1e1e")
chat = scrolledtext.ScrolledText(chat_frame, bg="#1e1e1e", fg="white", font=("Arial", 10))
chat.pack(side="left", fill="both", expand=True)
chat.config(state="disabled")
user_list = tk.Listbox(chat_frame, width=15, bg="#2b2b2b", fg="#00ff00", font=("Arial", 10))
user_list.pack(side="right", fill="y")

entry_frame = tk.Frame(root, bg="#1e1e1e")
entry = tk.Entry(entry_frame, bg="#2b2b2b", fg="white", font=("Arial", 11))
entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
entry.bind("<Return>", send_message)
tk.Button(entry_frame, text="Gönder", command=send_message, bg="#28a745", fg="white").pack(side="left", padx=2)
tk.Button(entry_frame, text="Çık", command=root.destroy, bg="#dc3545", fg="white").pack(side="left", padx=2)

root.mainloop()