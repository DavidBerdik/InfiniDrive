# Provides an FTP Server to allow interaction with InfiniDrive through an FTP client.
# Adapted from https://gist.github.com/risc987/184d49fa1a86e3c6c91c
import array, libs.drive_api as drive_api, socket, threading

from binascii import crc32
from hashlib import sha256
from io import BytesIO
from libs.upload_handler import handle_update_fragment
from libs.upload_handler import handle_upload_fragment
from PIL import Image

class FTPserverThread(threading.Thread):
	def __init__(self, pair, local_username, local_password, drive_service):
		conn, addr = pair
		self.conn = conn
		self.addr = addr # Client Address
		self.local_username = local_username
		self.local_password = local_password
		self.drive_service = drive_service
		self.rest = False
		self.pasv_mode = False
		self.input_username = ''
		threading.Thread.__init__(self)

	def run(self):
		self.conn.send(b'220 Welcome to the InfiniDrive FTP Interface!\r\n')
		while True:
			cmd_byte = self.conn.recv(32*1024)
			if not cmd_byte:
				break
			else:
				cmd = cmd_byte.decode('UTF-8')
				print('Received command:', cmd.strip())
				try:
					func = getattr(self,cmd[:4].strip().upper())
					func(cmd)
				except Exception as e:
					if(str(e)[:41] == "'FTPserverThread' object has no attribute"):
						# The command issued by the client is not implemented, so return an error stating so.
						self.conn.send(b'502 Command not implemented.\r\n')
					else:
						print('FTP SERVER ERROR:', e)
						self.conn.send(b'500 Sorry.\r\n')

	def SYST(self, cmd):
		# Answer client request for information about server.
		self.conn.send(b'215 InfiniDrive FTP Interface\r\n')

	def OPTS(self, cmd):
		# Answer that UTF8 is on. Otherwise just say sorry.
		if cmd[5:-2].upper() == 'UTF8 ON':
			self.conn.send(b'200 OK.\r\n')
		else:
			self.conn.send(b'451 Sorry.\r\n')

	def USER(self, cmd):
		# Accept username input.
		self.input_username = cmd.split()[1]
		self.conn.send(b'331 Password required for ' + self.input_username.encode('UTF-8') + b'\r\n')

	def PASS(self, cmd):
		# Accept password input and authenticate it.
		if self.local_username == self.input_username and self.local_password == cmd.split()[1]:
			self.conn.send(b'230 OK.\r\n')
		else:
			self.conn.send(b'530 Login incorrect.\r\n')

	def QUIT(self, cmd):
		# FTP logout command.
		self.conn.send(b'221 Goodbye.\r\n')

	def NOOP(self, cmd):
		# No-op command.
		self.conn.send(b'200 OK.\r\n')

	def TYPE(self, cmd):
		# The server always transfers data in binary mode.
		if(cmd.split()[1] == 'I'):
			self.conn.send(b'200 Binary mode.\r\n')
		else:
			self.conn.send(b'504 Only binary mode is supported.\r\n')

	def CDUP(self, cmd):
		# The command to change to the parent directory does not make sense with InfiniDrive, so deny it.
		self.conn.send(b'550 Permission denied.\r\n')
		
	def PWD(self, cmd):
		# The InfiniDrive FTP interface emulates "/" as the working directory.
		cwd='/'
		self.conn.send(('257 \"%s\"\r\n' % cwd).encode('utf-8'))

	def CWD(self, cmd):
		# The command to change the working directory does not make sense with InfiniDrive, so deny it.
		self.conn.send(b'550 Permission denied.\r\n')
			
	def PORT(self, cmd):
		# Specifies an address and port to which the server should connect
		if self.pasv_mode:
			self.servsock.close()
			self.pasv_mode = False
		l=cmd[5:].split(',')
		self.dataAddr='.'.join(l[:4])
		self.dataPort=(int(l[4])<<8)+int(l[5])
		self.conn.send(b'200 Get port.\r\n')

	def PASV(self, cmd):
		# Enter passive mode
		# Adapted from https://xiaoxia.org/2011/05/10/again-more-than-400-lines-of-python-code-to-achieve-a-ftp-server/
		self.pasv_mode = True
		self.servsock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		#self.servsock.bind((local_ip,0))
		local_ip, port = self.conn.getsockname()
		self.servsock.bind((local_ip,0))		
		self.servsock.listen(1)
		ip, port = self.servsock.getsockname()
		print('Open:', ip, port)
		self.conn.send(('227 Entering Passive Mode (%s,%u,%u).\r\n' % (','.join(ip.split('.')), port>>8&0xFF, port&0xFF)).encode('UTF-8'))

	def start_datasock(self):
		# Start data socket
		if self.pasv_mode:
			self.datasock, addr = self.servsock.accept()
			print('Connect:', addr)
		else:
			self.datasock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			self.datasock.connect((self.dataAddr,self.dataPort))

	def stop_datasock(self):
		# Stop data socket
		self.datasock.close()
		if self.pasv_mode:
			self.servsock.close()

	def SIZE(self, cmd):
		# Gets the size of an InfiniDrive file
		filename = cmd[5:-2].lstrip('/')
		try:
			file_size = drive_api.get_file_size(self.drive_service, filename)
			self.conn.send(('213 ' + str(file_size) + '\r\n').encode('UTF-8'))
		except:
			self.conn.send(b'550 File not found.\r\n')

	def LIST(self, cmd):
		# Get the list of InfiniDrive files		
		self.conn.send(b'150 Here comes the directory listing.\r\n')
		remote_files = [item for sublist in drive_api.list_files(self.drive_service) for item in sublist]
		self.start_datasock()
		for file in remote_files:
			self.datasock.send(("-rwxrwxrwx   1 owner   group          0 Jan 01  0:00 " + file + "\r\n").encode('UTF-8'))
		self.stop_datasock()
		self.conn.send(b'226 Directory send OK.\r\n')

	def MKD(self, cmd):
		# Make directory command: we do not want the user to be able to make directories, so always deny permission.
		self.conn.send(b'550 Permission denied.\r\n')

	def RMD(self, cmd):
		# Remove directory command: this command does not make sense in the context of InfiniDrive, so always deny permission.
		self.conn.send(b'550 Permission denied.\r\n')

	def DELE(self, cmd):
		# Deletes an InfiniDrive file
		filename = cmd[5:-2]
		try:
			drive_api.delete_file(self.drive_service, filename)
			self.conn.send(b'250 File deleted.\r\n')
		except:
			self.conn.send(b'450 Delete failed.\r\n')

	def RNFR(self, cmd):
		# Rename from command: store the current name of the file the user wants to rename.
		self.rnfn = cmd[5:-2]
		self.conn.send(b'350 Ready.\r\n')

	def RNTO(self, cmd):
		# Rename to command: renames an InfiniDrive file
		filename = cmd[5:-2]
		try:
			drive_api.rename_file(self.drive_service, self.rnfn, filename)
			self.conn.send(b'250 File renamed.\r\n')
		except:
			self.conn.send(b'550 Rename failed.\r\n')

	def REST(self, cmd):
		# Set file transfer position
		self.pos = int(cmd[5:-2])
		self.rest = True
		self.conn.send(b'250 File transfer position set.\r\n')

	def RETR(self, cmd):
		# Downloads an InfiniDrive file
		# Extract the name of the file to download from the command
		filename = cmd[5:-2].lstrip('/')

		# Open the data socket.
		print('Downloading', filename)
		self.conn.send(b'150 Opening data connection.\r\n')
		self.start_datasock()

		if not drive_api.file_with_name_exists(self.drive_service, filename):
			# Check if the file exists. If it does not, close the socket and send an error.
			self.stop_datasock()
			self.conn.send(b'551 File does not exist.\r\n')
			return

		# Get a list of the fragments that make up the given InfiniDrive file.
		files = drive_api.get_files_list_from_folder(self.drive_service, drive_api.get_file_id_from_name(self.drive_service, filename))

		# If the client has requested a custom starting position, slice off irrelevant fragments and calculate the fragment byte offset.
		if self.rest:
			files = files[:-(self.pos // 10224000)]
			self.frag_byte_offset = self.pos % 10224000

		# For all fragments...
		for file in reversed(files):
			# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
			while True:
				try:
					pixelVals = list(Image.open(drive_api.get_image_bytes_from_doc(self.drive_service, file)).convert('RGB').getdata())
				except:
					continue
				pixelVals = [j for i in pixelVals for j in i]
				if len(pixelVals) == 10224000:
					break

			# Compare the hashes stored with document to the hashes of pixelVals. If they do not match, terminate download and report corruption.
			if('properties' in file and (file['properties']['crc32'] != hex(crc32(bytearray(pixelVals))) or
			  ('sha256' in file['properties'] and file['properties']['sha256'] != sha256(bytearray(pixelVals)).hexdigest()))):
				self.stop_datasock()
				self.conn.send(b'551 File is corrupted.\r\n')
				return

			# Build the final byte array.
			pixelVals = array.array('B', pixelVals).tobytes().rstrip(b'\x00')[:-1]

			# If the client requested a custom starting position, slice off the start of the byte array using the calculated frag_byte_offset value.
			if self.rest:
				pixelVals = pixelVals[self.frag_byte_offset:]
				self.rest = False

			# Send the byte array to the client.
			self.datasock.send(pixelVals)

		# File transfer is complete. Close the data socket and report completion.
		self.stop_datasock()
		self.conn.send(b'226 Transfer complete.\r\n')

	def STOR(self, cmd):
		# Uploads an InfiniDrive file
		# Extract the name of the file to upload from the command
		filename = cmd[5:-2].lstrip('/')

		# Open the data socket.
		print('Uploading:', filename)
		self.conn.send(b'150 Opening data connection.\r\n')
		self.start_datasock()

		# If a file with the given name does not already exist, create a new InfiniDrive file for the fragments.
		if not drive_api.file_with_name_exists(self.drive_service, filename):
			drive_api.begin_storage(filename)

		# Get the ID of the InfiniDrive file (the folder that will store the fragments.
		dirId = drive_api.get_file_id_from_name(self.drive_service, filename)

		# Get a list of the fragments that currently make up the file. If this is a new upload, it should come back empty.
		orig_fragments = drive_api.get_files_list_from_folder(self.drive_service, dirId)
		orig_fragments.reverse()

		# Store the fragment number.
		docNum = 1

		# Used to keep track of the numbers for fragments that have failed uploads.
		failedFragmentsSet = set()

		# Receive file data in chunks from the client.
		while True:
			fileBytes = self.datasock.recv(10223999)
			
			# If no data is received from the client, exit the loop.
			if not fileBytes:
				break

			if docNum <= len(orig_fragments):
				# A remote fragment is present, so update it.
				# First, extract the hash value if present.
				currentHashCrc32 = ''
				currentHashSha256 = ''
				if 'properties' in orig_fragments[docNum-1]:
					currentHashCrc32 = orig_fragments[docNum-1]['properties']['crc32']
					if 'sha256' in orig_fragments[docNum-1]['properties']:
						currentHashSha256 = orig_fragments[docNum-1]['properties']['sha256']
				# Process update.
				handle_update_fragment(drive_api, fileBytes, currentHashCrc32, currentHashSha256, self.drive_service, orig_fragments[docNum-1]['id'], docNum, BytesIO())
			else:
				# Process the fragment and upload it to Google Drive.
				handle_upload_fragment(drive_api, fileBytes, self.drive_service, dirId, docNum, failedFragmentsSet, BytesIO())

			# Increment docNum for next Word document.
			docNum = docNum + 1

		# Close the socket and report a successful file transfer.
		self.stop_datasock()
		self.conn.send(b'226 Transfer complete.\r\n')

		# For each document number in failedFragmentsSet, check for duplicates and remove any if they are present.
		for name in failedFragmentsSet:
			# Get duplicates.
			duplicates = drive_api.get_files_with_name_from_folder(self.drive_service, dirId, name)

			# For tracking if we should check data validity
			checkDataValidity = True

			# For each entry in the duplicates array...
			for file in duplicates:
				if checkDataValidity:
					# If we should check data validity, retrieve the file data and compare the hashes.
					fileData = bytearray([j for i in list(Image.open(drive_api.get_image_bytes_from_doc(self.drive_service, file)).convert('RGB').getdata()) for j in i])

					if(file['properties']['crc32'] == hex(crc32(fileData)) and file['properties']['sha256'] == sha256(fileBytes).hexdigest()):
						# If the hashes are identical, mark for no further validity checks and do not delete the file.
						checkDataValidity = False
					else:
						# If the hashes do not match, delete the fragment.
						drive_api.delete_file(self.drive_service, file['id'])
				else:
					# If we should not check data validity, delete the file.
					drive_api.delete_file(self.drive_service, file['id'])

class FTPserver(threading.Thread):
	def __init__(self, local_username, local_password, port):
		self.local_username = local_username
		self.local_password = local_password
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind(('localhost', port))
		threading.Thread.__init__(self)

	def run(self):
		self.sock.listen(5)
		while True:
			th = FTPserverThread(self.sock.accept(), self.local_username, self.local_password, drive_api.get_service())
			th.daemon = True
			th.start()

	def stop(self):
		self.sock.close()

def init_ftp_server(user='user', password='password', port=21):
	# Initializes the FTP server that interfaces with InfiniDrive
	ftp = FTPserver(user, password, port)
	ftp.daemon = True
	ftp.start()
	print('InfiniDrive FTP Interface Server Started!')
	input('Press enter key to shut down server.\n')
	ftp.stop()