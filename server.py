import calendar
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
ROOTDIR='.'
#HTTP Status
STATUS={
    200:"OK",
    400:"Bad Request",
    403:"Forbidden",
    404:"Not Found",
    304:"Not Modified",
}
def client(socket: socket.socket,addr:tuple):
    ip=addr[0] #get the ip address of the client
    while True:
        buffer=b''
        #loop to receive the data until it reads the end of the http request header
        while b'\r\n\r\n' not in buffer:
            temp=socket.recv(1024)
            if not temp:
                socket.close()
                return
            buffer+=temp
        try:
            data=buffer.decode()
            if not data.strip():
                break
            # split the request in lines
            lines=data.split("\r\n")
            #get the request line
            request=lines[0]
            #get the request headers
            headers={}
            for line in lines[1:]:
                if ": " in line:
                    key,value=line.split(": ",1)
                    headers[key.lower()]=value.strip()
            #get the request method,url and the version of http
            parts=request.split()
            #if the format of the request is incorrect, return 400 code
            if len(parts) <3:
                socket.sendall(build_response(400, None, 'GET', 'close'))
                log(ip,request,400)
                break
            #get the request method
            method=parts[0].upper()
            #get the request url
            url=parts[1]
            version=parts[2] #get the version of http
            #if the method is not GET or HEAD, then return 400
            if method not in ["GET","HEAD"]:
                socket.sendall(build_response(400,None,'GET','close'))
                log(ip,url,400)
                break
            #if the request url is root, map it to index.html
            if url=='/':
                url="/index.html"
            #combine the file path and decode the URL
            file_path=os.path.join(ROOTDIR,unquote_plus(url).lstrip("/"))
            status=get_file_status(file_path,headers)
            conn_header=headers.get('connection', '').lower()
            #If http version is 1.1, default connection is keep-alive,
            #If it is 1.0, the default connection is close
            if conn_header=='close':
                 connection='close'
            elif version=='HTTP/1.0' and conn_header!='keep-alive':
                connection='close'
            else:
                connection='keep-alive'
            #build the response and send it to client
            response=build_response(status,file_path,method,connection)
            socket.sendall(response)
            log(ip,url,status) #log the file
            if connection=='close':
                break

        except Exception as e:
            break
    socket.close()

#function to log the client information to log.txt
def log(ip,file,status):
    #Get the timestamp in GMT format
    timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S GMT")
    #combine the status code with description
    status=f"{status} {STATUS.get(status, '')}"
    #append the log information to log.txt
    with open(FILE,'a' ) as f:
        f.write(f"{ip},{file},{timestamp},{status}\n")
#function to check whether the request file is legal
def get_file_status(path,headers) ->int:
    #if file doesn't exist, return 404
    try:
        if not os.path.isfile(path):
            return 404
        abs_path = os.path.abspath(path)
        abs_root = os.path.abspath(ROOTDIR)
        if not abs_path.startswith(abs_root):
            return 403
        # If the file cannot be read, return 403
        if not os.access(path, os.R_OK):
            return 403
        try:
            with open(path,'rb') as f:
                pass
        except PermissionError:
            return 403
        except Exception as e:
            return 403
        if 'if-modified-since' in headers:
            try:
                # compare the file last modified time and if modified time,
                # if not modified, then return 304
                if_modified_string = headers['if-modified-since']
                client_gmt = calendar.timegm(time.strptime(if_modified_string, '%a, %d %b %Y %H:%M:%S GMT'))
                file_modified_time = os.path.getmtime(path)
                file_gmt = calendar.timegm(time.gmtime(file_modified_time))
                if file_gmt <= client_gmt:
                    return 304
            except:
                pass
        return 200
    except Exception as e:
       return 403
#function to build the HTTP response, combine the header and the body
def build_response(status,path,method,connection)->bytes:
    status_line=f"HTTP/1.1 {status} {STATUS.get(status, 'Unknown')}\r\n"
    headers=[
        "Server: Web-server\r\n",
        f"Date: {datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n",
    ]
    body=b''
    #if the request is successful, then return the content of the file
    if status==200 and path is not None and os.path.isfile(path):
        modified_time=time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(os.path.getmtime(path)))
        headers.append(f"Last-Modified: {modified_time}\r\n")
        #get the type of the request file
        content_type, _=mimetypes.guess_type(path)
        #if unknown type, then default as arbitrary binary data
        if not content_type:
            content_type='application/octet-stream'
        headers.append(f"Content-Type: {content_type}\r\n")
        #if the method is GET, then read the file content as the body
        if method=='GET':
            with open(path,'rb') as f:
                body=f.read()
            headers.append(f"Content-Length: {len(body)}\r\n")
        #if the method is HEAD, only return the header
        else:
            headers.append("Content-Length: 0\r\n")
    #If it is error, render an error.html and return
    elif status in (400,403,404):
        error=f"<html><body><h1>{status} {STATUS.get(status)}</h1></body></html>"
        body=error.encode()
        headers.append("Content-Type: text/html\r\n")
        headers.append(f"Content-Length: {len(body)}\r\n")
    #If cache is not expired, only return the header
    elif status ==304:
        if path and os.path.isfile(path):
            modified_time=time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(os.path.getmtime(path)))
            headers.append(f"Last-Modified: {modified_time}\r\n")
        headers.append("Content-Length: 0\r\n")
    #append the connection status
    headers.append(f"Connection: {connection}\r\n")
    #comibine the response with status line, header, empty line, and the response body
    response=status_line.encode()
    for header in headers:
        response+=header.encode()
    response+=b'\r\n'
    if method=='GET' or status in (400,403,404):
        response+=body
    return response


def main():
    #create the TCP socket
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #set the port multiplexing
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #bind the IP and port
    serversocket.bind((HOST, PORT))
    serversocket.listen(5)
    print("server started")
    #infinite loop to accept the client connection
    while True:
        clientsocket, addr = serversocket.accept()
        #start a thread to handle the client request
        thread=threading.Thread(target=client,args=(clientsocket,addr))
        thread.daemon=True
        thread.start()
if __name__ == "__main__":
    main()