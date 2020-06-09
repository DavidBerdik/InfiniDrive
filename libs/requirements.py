class requirements:        
	def __init__(self):
		if self.check_imports() and self.check_credentials():
			return
		quit()

	def check_imports(self):
		try:
			import array, gc, libs.drive_api as drive_api, math, os, os.path, pickle, requests, sys, time, zipfile
			from apiclient.http import MediaIoBaseDownload
			from apiclient.http import MediaIoBaseUpload
			from binascii import crc32
			from docx import Document
			from googleapiclient.discovery import build
			from google_auth_oauthlib.flow import InstalledAppFlow
			from google.auth.transport.requests import Request
			from hashlib import sha256
			from io import BytesIO
			from libs.bar import getpatchedprogress
			from libs.help import print_help
			from libs.upload_handler import handle_update_fragment
			from libs.upload_handler import handle_upload_fragment
			from PIL import Image
			from progress.bar import ShadyBar
			from progress.spinner import Spinner
			from tabulate import tabulate
		except (ModuleNotFoundError, ImportError) as error:
			print('\nOops! ', end = ' ')
			print(error)
			print('\nOne or more InfiniDrive dependencies are not installed on your system.')
			print('Using pip, you can install these dependencies using one of the following commands from the root InfiniDrive directory:')
			print('\t1. pip install -r requirements.txt\n\t2. python -m pip install -r requirements.txt')
			print('\nMore information is available in \'README.md\' as well as online at https://github.com/DavidBerdik/InfiniDrive')
			return False
		return True

	def check_credentials(self):
		import os
		if not os.path.exists('credentials.json'):
			print('InfiniDrive could not start because you have not provided a \'credentials.json\' file.')
			print('Please do so and try again. Instructions for doing this are available in \'README.md\'')
			print('as well as online at https://github.com/DavidBerdik/InfiniDrive')
			return False
		elif not os.path.exists('token.pickle'):
			print('Please complete account authentication using the following URL.')
			print('You can then run your previous command again.\n')
			import libs.drive_api as drive_api
			drive_api.get_service()
			return False
		return True

requirements()