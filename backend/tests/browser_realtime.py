"""Small standard-library CDP driver for tests that await real IndexedDB I/O.

Virtual-time budgets can finish before IndexedDB callbacks arrive. This driver
polls with wall time, without changing the application's storage implementation.
"""
import base64
import json
import functools
import http.server
import threading
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


class DevTools:
    def __init__(self,url):
        parsed=urlsplit(url);self.socket=socket.create_connection((parsed.hostname,parsed.port),timeout=10);self.buffer=b'';self.serial=0
        key=base64.b64encode(os.urandom(16)).decode()
        request=f'GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost\r\n\r\n'
        self.socket.sendall(request.encode())
        while b'\r\n\r\n' not in self.buffer:self.buffer+=self.socket.recv(4096)
        header,self.buffer=self.buffer.split(b'\r\n\r\n',1)
        if b' 101 ' not in header:raise RuntimeError(header.decode())
    def read(self,length):
        while len(self.buffer)<length:
            chunk=self.socket.recv(65536)
            if not chunk:raise ConnectionError('Chrome disconnected')
            self.buffer+=chunk
        result,self.buffer=self.buffer[:length],self.buffer[length:];return result
    def send(self,data,opcode=1):
        mask=os.urandom(4);size=len(data);header=bytes([0x80|opcode])
        if size<126:header+=bytes([0x80|size])
        elif size<=65535:header+=bytes([0x80|126])+struct.pack('!H',size)
        else:header+=bytes([0x80|127])+struct.pack('!Q',size)
        self.socket.sendall(header+mask+bytes(value^mask[i%4] for i,value in enumerate(data)))
    def receive(self):
        chunks=[]
        while True:
            first,second=self.read(2);opcode=first&15;size=second&127
            if size==126:size=struct.unpack('!H',self.read(2))[0]
            elif size==127:size=struct.unpack('!Q',self.read(8))[0]
            mask=self.read(4) if second&128 else None;data=self.read(size)
            if mask:data=bytes(value^mask[i%4] for i,value in enumerate(data))
            if opcode==8:raise ConnectionError('Chrome closed WebSocket')
            if opcode==9:self.send(data,10);continue
            if opcode==10:continue
            chunks.append(data)
            if first&128:return json.loads(b''.join(chunks))
    def call(self,method,params=None):
        self.serial+=1;serial=self.serial;self.send(json.dumps(dict(id=serial,method=method,params=params or {})).encode())
        while True:
            reply=self.receive()
            if reply.get('id')==serial:
                if 'error' in reply:raise RuntimeError(reply['error'])
                return reply.get('result',{})
    def evaluate(self,expression):return self.call('Runtime.evaluate',dict(expression=expression,returnByValue=True))['result'].get('value')
    def close(self):self.socket.close()


def check_pages(fixture,output_dir,widths=(1280,800,768,600,375,320),assets=None,label="Browser"):
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    chrome=next((shutil.which(name) for name in ['google-chrome','google-chrome-stable','chromium','chromium-browser'] if shutil.which(name)),None)
    if not chrome:raise SystemExit('Chrome is required')
    results=[]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        root=Path(directory);profile=root/'profile';(root/'fixture.html').write_text(fixture())
        for route,path in (assets or {}).items():
            target=root/route.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        site=f'http://127.0.0.1:{server.server_address[1]}'
        process=subprocess.Popen([chrome,'--headless=new','--no-sandbox','--disable-gpu','--disable-background-networking','--allow-file-access-from-files','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--remote-allow-origins=http://localhost','--window-size=1400,1800',f'--user-data-dir={profile}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+15;port_file=profile/'DevToolsActivePort'
            while not port_file.exists():
                if process.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Chrome remote debugging did not start')
                time.sleep(.05)
            port=int(port_file.read_text().splitlines()[0]);base=f'http://127.0.0.1:{port}'
            for width in widths:
                host=root/f'host-{width}.html';host.write_text(f'''<!doctype html><html data-layout-status="pending"><head><meta charset="utf-8"><style>body{{margin:0}}iframe{{border:0;width:{width}px;height:1800px}}</style><script>addEventListener('message',event=>{{if(event.source!==document.querySelector('iframe')?.contentWindow)return;document.documentElement.dataset.layoutStatus=event.data.layoutStatus;document.documentElement.dataset.layoutMessage=event.data.message||'';}});</script></head><body><iframe src="fixture.html"></iframe></body></html>''')
                request=urllib.request.Request(base+'/json/new?about:blank',method='PUT')
                with urllib.request.urlopen(request,timeout=10) as response:target=json.load(response)
                client=DevTools(target['webSocketDebuggerUrl'])
                try:
                    client.call('Emulation.setDeviceMetricsOverride',dict(width=1400,height=1800,deviceScaleFactor=1,mobile=False))
                    client.call('Page.bringToFront');client.call('Page.navigate',dict(url=site+'/'+host.name));deadline=time.monotonic()+20
                    while time.monotonic()<deadline:
                        status=client.evaluate('document.documentElement.dataset.layoutStatus')
                        if status in ('pass','fail'):break
                        time.sleep(.05)
                    message=client.evaluate('document.documentElement.dataset.layoutMessage') or 'Offline fixture did not finish'
                    passed=status=='pass';results.append(dict(width=width,passed=passed,message='' if passed else message))
                    (output_dir/f'{width}.html').write_text(client.evaluate('document.documentElement.outerHTML') or '')
                    shot=client.call('Page.captureScreenshot',dict(format='png',captureBeyondViewport=False))
                    (output_dir/f'{width}.png').write_bytes(base64.b64decode(shot['data']))
                    print(f'{label} {width}px: '+('PASS' if passed else 'FAIL '+message),flush=True)
                finally:
                    client.close()
                    with urllib.request.urlopen(base+'/json/close/'+target['id'],timeout=10):pass
        finally:
            server.shutdown();server.server_close()
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    (output_dir/'results.json').write_text(json.dumps(results,indent=2))
    if not all(row['passed'] for row in results):raise SystemExit(1)
