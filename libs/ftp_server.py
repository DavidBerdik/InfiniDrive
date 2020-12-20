# Provides an FTP Server to allow interaction with InfiniDrive through an FTP client.
# Adapted from https://gist.github.com/risc987/184d49fa1a86e3c6c91c
import array, gc, libs.drive_api as drive_api, libs.hash_handler as hash_handler, libs.time_bomb as time_bomb, libs.upload_handler as upload_handler, socket, threading

from os import mkdir
from os import remove
from os.path import exists
from PIL import Image
from shutil import rmtree

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

		# Get a count of the number of fragments that make up the file.
		fragment_count = drive_api.get_fragment_count(self.drive_service, filename)

		# For indexing fragments.
		fragment_index = 1

		# Get the InfiniDrive file ID from its name
		file_id = drive_api.get_file_id_from_name(self.drive_service, filename)

		# If the client has requested a custom starting position, slice off irrelevant fragments and calculate the fragment byte offset.
		if self.rest:
			fragment_index = self.pos // 10223999 + 1
			self.frag_byte_offset = self.pos % 10223999

		# Asynchronously retrieve a list of all files. We do this so that we can reduce Drive API calls, but if we wait for the list,
		# the FTP client will likely time out before we can finish, so we will retrieve one fragment at a time at first while the
		# entire list is retrieved in the background here.
		files = list()
		threading.Thread(target=drive_api.get_files_list_from_folder_async, args=(drive_api.get_service(), file_id, files)).start()

		# For all fragments...
		while fragment_index <= fragment_count:
			# Get the fragment with the given index
			file = None
			if files == []:
				# The fragment list is not available yet, so retrieve one fragment.
				file = drive_api.get_files_with_name_from_folder(self.drive_service, file_id, str(fragment_index))[0]
			else:
				# The fragment list is available, so use it to locate the fragment.
				file = files[0][fragment_index - 1]

			# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
			while True:
				try:
					pixelVals = list(Image.open(drive_api.get_image_bytes_from_doc(self.drive_service, file)).convert('RGB').getdata())
				except Exception as e:
					continue
				pixelVals = [j for i in pixelVals for j in i]
				if len(pixelVals) == 10224000:
					break

			# If the downloaded values do not match the fragment hash, terminate download and report corruption.
			if hash_handler.is_download_invalid(file, bytearray(pixelVals)):
				self.stop_datasock()
				self.conn.send(b'551 File is corrupted.\r\n')
				return

			# Strip the null byte padding and "spacer byte" from pixelVals.
			pixelVals = array.array('B', pixelVals).tobytes().rstrip(b'\x00')[:-1]

			# If the client requested a custom starting position, slice off the start of the byte array using the calculated frag_byte_offset value.
			if self.rest:
				pixelVals = pixelVals[self.frag_byte_offset:]
				self.rest = False

			# Send the byte array to the client.
			self.datasock.send(pixelVals)

			# Increment fragment_index
			fragment_index += 1

		# File transfer is complete. Close the data socket and report completion.
		self.stop_datasock()
		self.conn.send(b'226 Transfer complete.\r\n')

	def STOR(self, cmd):
		# Uploads an InfiniDrive file
		# If Google's new quota rules are being enforced, deny uploading permission and return.
		if time_bomb.is_quota_enforced():
			self.conn.send(b'550 As of June 1, 2021, InfiniDrive no longer permits uploads. More information: https://blog.google/products/photos/storage-policy-update/\r\n')
			return
		
		# Extract the name of the file to upload from the command
		file_name = str(cmd[5:-2].lstrip('/'))

		# If a file with the given name does not already exist, create a new InfiniDrive file for the fragments.
		if not drive_api.file_with_name_exists(self.drive_service, file_name):
			drive_api.begin_storage(file_name)

		# Open file for writing.
		file_handle = open('ftp_upload_cache/' + str(file_name), 'wb')

		# Open the data socket.
		print('Uploading:', str(file_name))
		self.conn.send(b'150 Opening data connection.\r\n')
		self.start_datasock()

		# Receive the file from the client.
		while True:
			data = self.datasock.recv(1024)
			if not data:
				break
			file_handle.write(data)
		file_handle.close()

		# Close the socket and report a successful file transfer.
		self.stop_datasock()
		self.conn.send(b'226 Transfer complete.\r\n')

		# Trigger asynchronous upload of the file to Google Drive.
		threading.Thread(target=self.async_file_upload, args=(file_name,)).start()

	def async_file_upload(self, file_name):
		# Used asynchronously for uploading a file to InfiniDrive after it has been uploaded and cached on the FTP server.
		print('Starting asynchronous upload of ' + str(file_name) + '.')

		# Get Drive service.
		drive_connect = drive_api.get_service()

		# Get directory ID.
		dir_id = drive_api.get_file_id_from_name(drive_connect, file_name)

		# Get a list of the fragments that currently make up the file. If this is a new upload, it should come back empty.
		orig_fragments = drive_api.get_files_list_from_folder(drive_connect, dir_id)

		# Set chunk size for reading files to 9.750365257263184MB (10223999 bytes)
		read_chunk_sizes = 10223999

		# Doc number
		doc_num = 1

		# Used to keep track of the numbers for fragments that have failed uploads.
		failed_fragments = set()

		# Iterate through file in chunks.
		infile = open('ftp_upload_cache/' + str(file_name), 'rb')

		# Read an initial chunk from the file.
		file_bytes = infile.read(read_chunk_sizes)

		# Keep looping until no more data is read.
		while file_bytes:
			if doc_num <= len(orig_fragments):
				# A remote fragment is present, so update it.
				upload_handler.handle_update_fragment(drive_api, orig_fragments[doc_num-1], file_bytes, drive_connect, doc_num)
			else:
				# Process the fragment and upload it to Google Drive.
				upload_handler.handle_upload_fragment(drive_api, file_bytes, drive_connect, dir_id, doc_num, failed_fragments)

			# Increment docNum for next Word document and read next chunk of data.
			doc_num = doc_num + 1
			file_bytes = infile.read(read_chunk_sizes)

			# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
			gc.collect()

		infile.close()

		# If an update took place and the new file had fewer fragments than the previous file, delete any leftover fragments from the previous upload.
		doc_num = doc_num - 1
		while doc_num < len(orig_fragments):
			drive_api.delete_file_by_id(drive_connect, orig_fragments[doc_num]['id'])
			doc_num = doc_num + 1

		# Process fragment upload failures
		upload_handler.process_failed_fragments(drive_api, failed_fragments, dir_id)

		# Delete the local cache of the file.
		remove('ftp_upload_cache/' + str(file_name))

		# Report completion of the asynchronous upload.
		print('Asynchronous upload of ' + str(file_name) + ' complete.')

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

def init_ftp_server(user, password, port):
	# Initializes the FTP server that interfaces with InfiniDrive

	# Recreate the FTP server upload cache directory
	if exists('ftp_upload_cache'):
		rmtree('ftp_upload_cache')
	mkdir('ftp_upload_cache')

	# Initialize the FTP server
	ftp = FTPserver(user, password, port)
	ftp.daemon = True
	ftp.start()
	print('InfiniDrive FTP Interface Server Started!')
	print('NOTE: The FTP server binds to localhost. Only connections from localhost will be accepted.')
	input('To shut down server, press enter key.\n\n')

	# Enter key was pressed. Stop server and delete FTP server upload cache directory.
	ftp.stop()
	rmtree('ftp_upload_cache')