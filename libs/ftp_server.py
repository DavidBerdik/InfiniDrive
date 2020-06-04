from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

class InfiniDriveFTPHandler(FTPHandler):
	pass

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