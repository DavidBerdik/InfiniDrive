import libs.driveAPI as driveAPI

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import BufferedIteratorProducer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

drive_service = driveAPI.get_service()

class InfiniDriveFTPHandler(FTPHandler):
	def ftp_LIST(self, path):
		# Get list of files
		remote_files = [item for sublist in driveAPI.list_files(drive_service) for item in sublist]
		iterator = self.format_file_list(remote_files)
		producer = BufferedIteratorProducer(iterator)
		self.push_dtp_data(producer, isproducer=True, cmd="LIST")
		return path

	def ftp_NLST(self, path):
		# Get list of files
		return self.ftp_LIST(path)
	
	def ftp_STAT(self, path):
		# Get list of files
		return self.ftp_LIST(path)

	def ftp_MLSD(self, path):
		# Get list of files
		return self.ftp_LIST(path)

	def ftp_MLST(self, path):
		# Get list of files
		return self.ftp_LIST(path)

	def format_file_list(self, files):
		# Emulates the output of "/bin/ls -lA" but fakes all other data for compatibility.
		for file in files:
			line = "-rwxrwxrwx   1 owner   group          0 Jan 01  0:00 " + file + "\r\n"
			yield line.encode('utf8')

def init_ftp_server(user='user', password='password', port=21):
	# Initializes the FTP server that interfaces with InfiniDrive

	# Create authorizer for the server using the given username and password.
	authorizer = DummyAuthorizer()
	authorizer.add_user(user, password, '.', perm='lrdfw')

	# Initialize InfiniDrive FTP Handler
	handler = InfiniDriveFTPHandler
	handler.authorizer = authorizer

	# InfiniDrive FTP Server Banner
	handler.banner = "Welcome to the InfiniDrive FTP server."

	# Create the server. It should listen on 0.0.0.0:port
	server = FTPServer(('', port), handler)

	# Set maximum server connections
	server.max_cons = 256
	server.max_cons_per_ip = 5

	# Start running the FTP server
	server.serve_forever()