# 这是一个示例 Python 脚本。

# 按 Shift+F10 执行或将其替换为您的代码。
# 按 双击 Shift 在所有地方搜索类、文件、工具窗口、操作和设置。

import socket
import threading
import os
import time
import datetime
import mimetypes
from urllib.parse import unquote_plus
HOST= '127.0.0.1'
PORT = 8080
FILE='log.txt'
STATUS={
    200:"OK",
    400:"Bad Request",
    403:"Forbidden",
    404:"Not Found",
    304:"Not Modified",
}
def client(socket: socket.socket,addr:tuple):
    ip=addr[0]
    while True:
        try:


def main():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind((HOST, PORT))
    serversocket.listen(5)
    print("server started")
    while True:
        clientsocket, addr = serversocket.accept()
        thread=threading.Thread(target=client,args=(clientsocket,addr))
        thread.daemon=True
        thread.start()
if __name__ == "__main__":
    main()