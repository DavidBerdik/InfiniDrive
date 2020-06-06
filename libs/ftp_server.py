# Adapted from https://gist.github.com/risc987/184d49fa1a86e3c6c91c

import os, socket, sys, threading, time
import libs.driveAPI as driveAPI

allow_delete = True
local_port = 21
currdir=os.path.abspath('.')

class FTPserverThread(threading.Thread):
	def __init__(self, pair, local_username, local_password, drive_service):
		conn, addr = pair
		self.conn=conn
		self.addr=addr  # client address
		self.local_username=local_username
		self.local_password=local_password
		self.drive_service=drive_service
		self.basewd=currdir
		self.cwd=self.basewd
		self.rest=False
		self.pasv_mode=False
		self.input_username=''
		threading.Thread.__init__(self)

	def run(self):
		self.conn.send(b'220 Welcome!\r\n')
		while True:
			cmd_byte=self.conn.recv(32*1024)
			if not cmd_byte: break
			else:
				cmd = cmd_byte.decode('UTF-8')
				print ('Recieved:',cmd)
				try:
					func=getattr(self,cmd[:4].strip().upper())
					func(cmd)
				except Exception as e:
					print ('ERROR:',e)
					#traceback.print_exc()
					self.conn.send(b'500 Sorry.\r\n')

	def SYST(self,cmd):
		self.conn.send(b'215 UNIX Type: L8\r\n')
	def OPTS(self,cmd):
		if cmd[5:-2].upper()=='UTF8 ON':
			self.conn.send(b'200 OK.\r\n')
		else:
			self.conn.send(b'451 Sorry.\r\n')
	def USER(self,cmd):
		self.input_username = cmd.split()[1]
		self.conn.send(b'331 Password required for ' + self.input_username.encode() + b'\r\n')
	def PASS(self,cmd):
		print(self.local_username)
		print(self.local_password)
		print(cmd.split())
		if self.local_username == self.input_username and self.local_password == cmd.split()[1]:
			self.conn.send(b'230 OK.\r\n')
		else:
			self.conn.send(b'530 Login incorrect.\r\n')
	def QUIT(self,cmd):
		self.conn.send(b'221 Goodbye.\r\n')
	def NOOP(self,cmd):
		self.conn.send(b'200 OK.\r\n')
	def TYPE(self,cmd):
		self.mode=cmd[5]	#TYPE I
		self.conn.send(b'200 Binary mode.\r\n')

	def CDUP(self,cmd):
		#if not os.path.samefile(self.cwd,self.basewd):
		if self.cwd == self.basewd :
			pass
		elif os.path.commonprefix([self.cwd,self.basewd]) == self.basewd :
			#learn from stackoverflow
			self.cwd=os.path.abspath(os.path.join(self.cwd,'..'))
		else:
			self.cwd = self.basewd
		self.conn.send(b'200 OK.\r\n')
		
	def PWD(self,cmd):
		cwd=os.path.relpath(self.cwd,self.basewd)
		if cwd=='.':
			cwd='/'
		else:
			cwd='/'+cwd
		self.conn.send( ('257 \"%s\"\r\n' % cwd).encode('utf-8') )
	def CWD(self,cmd):
		chwd=cmd[4:-2]
		orignal = self.cwd
		if chwd=='/':
			self.cwd=self.basewd
		elif chwd[0]=='/':
			self.cwd=os.path.join(self.basewd,chwd[1:])
		else:
			self.cwd=os.path.join(self.cwd,chwd)
		if os.path.exists(self.cwd):
			self.conn.send(b'250 OK.\r\n')
		else:
			self.cwd = orignal
			self.conn.send(('550 %s: No such file or directory.\r\n'% chwd).encode('utf-8'))
			
	def PORT(self,cmd):
		if self.pasv_mode:
			self.servsock.close()
			self.pasv_mode = False
		l=cmd[5:].split(',')
		self.dataAddr='.'.join(l[:4])
		self.dataPort=(int(l[4])<<8)+int(l[5])
		self.conn.send(b'200 Get port.\r\n')

	def PASV(self,cmd): # from http://goo.gl/3if2U
		self.pasv_mode = True
		self.servsock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		#self.servsock.bind((local_ip,0))
		local_ip, port = self.conn.getsockname()
		self.servsock.bind((local_ip,0))		
		self.servsock.listen(1)
		ip, port = self.servsock.getsockname()
		print ('open', ip, port)
		self.conn.send( ('227 Entering Passive Mode (%s,%u,%u).\r\n' % (','.join(ip.split('.')), port>>8&0xFF, port&0xFF)).encode('UTF-8') )

	def start_datasock(self):
		if self.pasv_mode:
			self.datasock, addr = self.servsock.accept()
			print ('connect:', addr)
		else:
			self.datasock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			self.datasock.connect((self.dataAddr,self.dataPort))

	def stop_datasock(self):
		self.datasock.close()
		if self.pasv_mode:
			self.servsock.close()


	def LIST(self,cmd):
		# Get the list of InfiniDrive files		
		self.conn.send(b'150 Here comes the directory listing.\r\n')
		remote_files = [item for sublist in driveAPI.list_files(self.drive_service) for item in sublist]
		print ('list:', self.cwd)
		self.start_datasock()
		for file in remote_files:
			self.datasock.send(("-rwxrwxrwx   1 owner   group          0 Jan 01  0:00 " + file + "\r\n").encode())
		self.stop_datasock()
		self.conn.send(b'226 Directory send OK.\r\n')

	def MKD(self,cmd):
		dn=os.path.join(self.cwd,cmd[4:-2])
		os.mkdir(dn)
		self.conn.send(b'257 Directory created.\r\n')

	def RMD(self,cmd):
		dn=os.path.join(self.cwd,cmd[4:-2])
		if allow_delete:
			os.rmdir(dn)
			self.conn.send(b'250 Directory deleted.\r\n')
		else:
			self.conn.send(b'450 Not allowed.\r\n')

	def DELE(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-2])
		if allow_delete:
			os.remove(fn)
			self.conn.send(b'250 File deleted.\r\n')
		else:
			self.conn.send(b'450 Not allowed.\r\n')

	def RNFR(self,cmd):
		self.rnfn=os.path.join(self.cwd,cmd[5:-2])
		self.conn.send(b'350 Ready.\r\n')

	def RNTO(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-2])
		os.rename(self.rnfn,fn)
		self.conn.send(b'250 File renamed.\r\n')

	def REST(self,cmd):
		self.pos=int(cmd[5:-2])
		self.rest=True
		self.conn.send(b'250 File position reseted.\r\n')

	def RETR(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-2])
		#fn=os.path.join(self.cwd,cmd[5:-2]).lstrip('/')
		print ('Downlowding:',fn)
		if self.mode=='I':
			fi=open(fn,'rb')
		else:
			fi=open(fn,'r')
		self.conn.send(b'150 Opening data connection.\r\n')
		if self.rest:
			fi.seek(self.pos)
			self.rest=False
		data= fi.read(1024)
		self.start_datasock()
		while data:
			self.datasock.send(data)
			data=fi.read(1024)
		fi.close()
		self.stop_datasock()
		self.conn.send(b'226 Transfer complete.\r\n')

	def STOR(self,cmd):
		fn=os.path.join(self.cwd,cmd[5:-2])
		print ('Uplaoding:',fn)
		if self.mode=='I':
			fo=open(fn,'wb')
		else:
			fo=open(fn,'wb')
		self.conn.send(b'150 Opening data connection.\r\n')
		self.start_datasock()
		while True:
			data=self.datasock.recv(1024)
			if not data: break
			fo.write(data)
		fo.close()
		self.stop_datasock()
		self.conn.send(b'226 Transfer complete.\r\n')

class FTPserver(threading.Thread):
	def __init__(self, local_username, local_password, drive_service):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind(('localhost',local_port))
		self.local_username = local_username
		self.local_password = local_password
		self.drive_service = drive_service
		threading.Thread.__init__(self)

	def run(self):
		self.sock.listen(5)
		while True:
			th=FTPserverThread(self.sock.accept(), self.local_username, self.local_password, self.drive_service)
			th.daemon=True
			th.start()

	def stop(self):
		self.sock.close()

def init_ftp_server(user='user', password='password', port=21):
	# Initializes the FTP server that interfaces with InfiniDrive

	# Set port
	local_port = port

	# Start running the FTP server
	ftp=FTPserver(user, password, driveAPI.get_service())
	ftp.daemon=True
	ftp.start()
	input('Enter to end...\n')
	ftp.stop()