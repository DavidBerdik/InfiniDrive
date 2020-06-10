#!/usr/bin/python3

import array, os.path, pickle, zipfile

from apiclient.http import MediaIoBaseDownload
from apiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from io import BytesIO
from PIL import Image

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

#Creates Service object to allow interaction with Google Drive
def get_service():
	"""Shows basic usage of the Drive v3 API.
	Prints the names and ids of the first 10 files the user has access to.
	"""
	creds = None
	# The file token.pickle stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists('token.pickle'):
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'credentials.json', SCOPES)
			creds = flow.run_local_server()
		# Save the credentials for the next run
		with open('token.pickle', 'wb') as token:
			pickle.dump(creds, token)

	service = build('drive', 'v3', credentials=creds)
	return service

#Creates the InfiniDrive root folder and returns its ID.
def create_root_folder(service):
	root_meta = {
		'name': "InfiniDrive Root",
		'mimeType': 'application/vnd.google-apps.folder',
		'properties': {'infinidriveRoot': 'true'},
		'parents': []
	}
	root_folder = service.files().create(body=root_meta,
		fields='id').execute()

	# Hide the root folder folder
	service.files().update(fileId=root_folder['id'], removeParents='root').execute()

	return root_folder

#Gets the ID of the InfiniDrive root folder.
def get_root_folder_id(service):
	results = service.files().list(
		q="properties has {key='infinidriveRoot' and value='true'} and trashed=false",
		pageSize=1,
		fields="nextPageToken, files(id, name, properties)").execute()
	folders = results.get('files', [])

	if not folders:
		return create_root_folder(service)['id']
	else:
		return folders[0]['id']

# Checks if an InfiniDrive upload with the given name exists. Returns true if file with names exists, else false.
def file_with_name_exists(service, file_name):
	query = "(mimeType='application/vnd.google-apps.folder') and (trashed=False) and ('" + get_root_folder_id(service) + "' in parents) and name='" + str(file_name) + "'"
	page_token = None
	filesList = list()
	while True:
		param = {}
		
		if page_token:
			param['pageToken'] = page_token
		
		results = service.files().list(q=query, fields="nextPageToken, files(name)", **param).execute()
		filesList += results.get('files', [])
		
		page_token = results.get('nextPageToken')
		if not page_token:
			break
	
	return len(filesList) > 0

# Given a file name, returns the file ID.
def get_file_id_from_name(service, file_name):
	query = "(mimeType='application/vnd.google-apps.folder') and (trashed=False) and ('" + get_root_folder_id(service) + "' in parents) and name='" + str(file_name) + "'"
	page_token = None
	filesList = list()
	while True:
		param = {}
		
		if page_token:
			param['pageToken'] = page_token
		
		results = service.files().list(q=query, fields="nextPageToken, files(id)", **param).execute()
		filesList += results.get('files', [])
		
		page_token = results.get('nextPageToken')
		if not page_token:
			break
	
	if len(filesList) == 0: return ''
	return [file.get('id') for file in filesList][0]

#Creates a folder and returns its ID
def create_folder(service, file_path):
	folder_metadata = {
	'name': file_path,
	'mimeType': 'application/vnd.google-apps.folder',
	'parents': [get_root_folder_id(service)]
	}
	folder = service.files().create(body=folder_metadata, fields= 'id').execute()

	return folder.get('id')

#Stores a file into a folder
def store_doc(service, folderId, file_name, crc32, sha256, file_path):
	file_metadata = {
	'name': file_name,
	'mimeType': 'application/vnd.google-apps.document',
	'parents': [folderId],
	'properties': {
			'crc32': str(crc32),
			'sha256': str(sha256)
		}
	}
	media = MediaIoBaseUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
	service.files().create(body=file_metadata,
									media_body=media,
									fields = 'id').execute()

# Updates a given fragment
def update_fragment(service, frag_id, crc32, sha256, file_path):
	media = MediaIoBaseUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
	file_metadata = {
	'properties': {
			'crc32': str(crc32),
			'sha256': str(sha256)
		}
	}
	service.files().update(
		fileId=frag_id,
		body=file_metadata,
		media_body=media,
		fields='id').execute()

#Returns folder id and service object for document insertion into the folder
def begin_storage(file_path):
	service = get_service()
	folderId = create_folder(service, file_path)
	return service, folderId

#Lists folders and their IDs (excluding folders in Trash)
def list_files(service):
	query = "(mimeType='application/vnd.google-apps.folder') and (trashed=False) and ('" + get_root_folder_id(service) + "' in parents)"
	page_token = None
	filesList = list()
	while True:
		param = {}
		
		if page_token:
			param['pageToken'] = page_token
		
		results = service.files().list(q=query, fields="nextPageToken, files(name)", **param).execute()
		filesList += results.get('files', [])
		
		page_token = results.get('nextPageToken')
		if not page_token:
			break
	
	filesList = [[folder.get('name')] for folder in filesList]
	filesList.sort()
	return filesList

# Deletes the file with the given name.
def delete_file(service, file_name):
	service.files().delete(fileId=get_file_id_from_name(service, file_name)).execute()

# Deletes the file with the given ID.
def delete_file_by_id(service, file_id):
	service.files().delete(fileId=file_id).execute()

# Renames the file with the given name.
def rename_file(service, old_name, new_name):
	file = {'name': new_name}

	# Rename the file.
	service.files().update(
		fileId=get_file_id_from_name(service, old_name),
		body=file,
		fields='name').execute()

# Returns the size of the file with the given name in bytes.
def get_file_size(service, file_name):
	# Get a list of the files in the given folder.
	files = get_files_list_from_folder(service, get_file_id_from_name(service, file_name))
	
	# Get the bytes from the last fragment.
	last_frag_bytes_len = len(array.array('B', [j for i in list(Image.open(get_image_bytes_from_doc(service, files[0])).convert('RGB').getdata()) for j in i]) \
		.tobytes().rstrip(b'\x00')[:-1])
	
	# Calculate the number of bytes that make up the file.
	file_size = ((len(files) - 1) * 10223999) + last_frag_bytes_len
	return file_size

# Returns a list of files in a folder with the given ID
def get_files_list_from_folder(service, folderId):
	query = "'" +folderId + "' in parents"
	page_token = None
	files = list()
	while True:
		param = {}

		if page_token:
			param['pageToken'] = page_token

		results = service.files().list(q=query, fields='nextPageToken, files(id, name, properties)', **param).execute()
		files += results.get('files', []) #grabs all of the files from the folder

		page_token = results.get('nextPageToken')
		if not page_token:
			break
	files.reverse()
	return files

# Returns a list of files in a folder with the given ID with the given name
def get_files_with_name_from_folder(service, folderId, name):
	query = "'" + folderId + "' in parents and name='" + str(name) + "'"
	page_token = None
	files = list()
	while True:
		param = {}

		if page_token:
			param['pageToken'] = page_token

		results = service.files().list(q=query, fields='nextPageToken, files(id, name, properties)', **param).execute()
		files += results.get('files', []) #grabs all of the files from the folder

		page_token = results.get('nextPageToken')
		if not page_token:
			break
	return files

# Returns the bytes from an image in a document
def get_image_bytes_from_doc(service, file):
	# Download file to memory
	request = service.files().export_media(fileId=file['id'], mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
	fh = BytesIO()
	downloader = MediaIoBaseDownload(fh, request)
	done = False
	while done is False:
		status, done = downloader.next_chunk()

	# Extract image from file and return the image's bytes
	zipRef = zipfile.ZipFile(fh, 'r')
	imgBytes = zipRef.read('word/media/image1.png')
	zipRef.close()
	return BytesIO(imgBytes)
