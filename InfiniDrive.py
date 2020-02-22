#!/usr/bin/python3

import array, gc, libs.driveAPI as driveAPI, math, os, requests, sys, time

from io import BytesIO
from libs.bar import getpatchedprogress
from PIL import Image
from progress.bar import ShadyBar
from progress.spinner import Spinner
from tabulate import tabulate
from libs.uploadHandler import handle_upload_fragment

progress = getpatchedprogress()

def print_ascii_logo():
	print("\n            ,,,                         ,,,")
	print("      &@@@@@@@@@@@@@              @@@@@@@@@@@@@@")
	print("    @@@@@@@#    %@@@@@#        @@@@@@@@@@@@@@@@@@@@")
	print("  @@@@@@            #@@@     &@@@@@@@         @@@@@@")
	print(" @@@@@                @@@@  @@@@@@@             @@@@@")
	print(" @@@@                   @@@@@@@@@                @@@@@")
	print("@@@@@                    @@@@@@@                  @@@@")
	print("@@@@@                    @@@@@@                   @@@@#")
	print("@@@@@                   @@@@@@                    @@@@,")
	print("&@@@@                 &@@@@@@@@                  *@@@@")
	print(" @@@@@               @@@@@@@ @@@                 @@@@@")
	print("  @@@@@            *@@@@@@#   @@@               @@@@@")
	print("   @@@@@@#       @@@@@@@@      @@@@#          @@@@@@")
	print("    *@@@@@@@@@@@@@@@@@@          @@@@@@@@%@@@@@@@@")
	print("       #@@@@@@@@@@@@               *@@@@@@@@@@@*\n")
	print("InfiniDrive v1.0.11 - An unlimited Google Drive storage solution")
	print("by David Berdik, Steven Myrick, Noah Greenberg\n")

if not os.path.exists('credentials.json'):
	# Print an error message and exit if "credentials.json" is not present.
	print('InfiniDrive could not start because you have not provided a "credentials.json" file.')
	print('Please do so and try again. Instructions for doing this are available in "README.md"')
	print('as well as online at https://github.com/DavidBerdik/InfiniDrive')
elif not os.path.exists('token.pickle'):
	# Display welcome message if "token.pickle" does not exist and complete Drive API authentication.
	print_ascii_logo()
	print("Welcome to InfiniDrive! Please complete account authentication using the following URL.")
	print("You can then run your previous command again.\n")
	driveAPI.get_service()
elif (len(sys.argv) == 3 or len(sys.argv) == 4) and str(sys.argv[1]) == "upload":
	# Get the name to use for the file.
	if len(sys.argv) == 3:
		# Use file path as name
		file_name = str(sys.argv[2])
	else:
		# Use user-specified name
		file_name = str(sys.argv[3])
	
	# Determine if upload is taking place from an HTTP or HTTPS URL.
	urlUpload = False
	if sys.argv[2][0:4].lower() == 'http':
		urlUpload = True
		urlUploadHandle = requests.get(sys.argv[2], stream=True, allow_redirects=True)
	
	# Create Google Drive folder
	driveConnect, dirId = driveAPI.begin_storage(file_name)
	fileSize = -1 # If file is being uploaded from web server and size cannot be retrieved this will stay at -1.
	if urlUpload:
		try:
			fileSize = int(urlUploadHandle.headers.get('content-length'))
		except TypeError:
			pass
		if fileSize == -1:
			# If fileSize is set to -1, set totalFrags to "an unknown number of"
			totalFrags = 'an unknown number of'
	else:
		fileSize = os.stat(sys.argv[2]).st_size
		totalFrags = math.ceil(fileSize / 10223999)
	print('Upload started. Upload will be composed of ' + str(totalFrags) + ' fragments.\n')
	
	# Set chunk size for reading files to 9.750365257263184MB (10223999 bytes)
	readChunkSizes = 10223999
	
	# Doc number
	docNum = 1
	
	# Progress bar
	if fileSize == -1:
		# The file size is unknown
		upBar = Spinner('Uploading... ')
	else:
		# The file size is known
		upBar = ShadyBar('Uploading...', max=totalFrags)
	
	if urlUpload:
		# If the upload is taking place from a URL...		
		# Iterate through remote file until no more data is read.
		for fileBytes in urlUploadHandle.iter_content(chunk_size=readChunkSizes):
			# Advance progress bar
			upBar.next()
			
			# Process the fragment and upload it to Google Drive.
			handle_upload_fragment(driveAPI, fileBytes, driveConnect, dirId, docNum)
			
			# Increment docNum for next Word document.
			docNum = docNum + 1
			
			# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
			gc.collect()
	else:
		# If the upload is taking place from a file path...	
		# Get file byte size
		fileSize = os.path.getsize(sys.argv[2])
		
		# Iterate through file in chunks.
		infile = open(str(sys.argv[2]), 'rb')
		
		# Read an initial chunk from the file.
		fileBytes = infile.read(readChunkSizes)
		
		# Keep looping until no more data is read.
		while fileBytes:
			# Advance progress bar
			upBar.next()

			# Process the fragment and upload it to Google Drive.
			handle_upload_fragment(driveAPI, fileBytes, driveConnect, dirId, docNum)

			# Increment docNum for next Word document and read next chunk of data.
			docNum = docNum + 1
			fileBytes = infile.read(readChunkSizes)

			# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
			gc.collect()
		
		infile.close()
	
	upBar.finish()
	print('\nUpload complete!')
	print('To download, use the following folder ID: ' + dirId)
elif len(sys.argv) == 2 and str(sys.argv[1]) == "list":
	filesList = driveAPI.list_files(driveAPI.get_service())
	
	if(len(filesList) == 0):
		print('No InfiniDrive uploads found')
	else:
		print(tabulate(filesList, headers=['File Name', 'File ID'], tablefmt="psql"))
elif len(sys.argv) == 4 and str(sys.argv[1]) == "download":
	# Get a list of the files in the given folder.
	files = driveAPI.get_files_list_from_folder(driveAPI.get_service(), str(sys.argv[2]))
	
	# Open a file at the user-specified path to write the data to
	result = open(str(sys.argv[3]), "wb")
	
	# For all files that are in the list...
	total = len(files)
	count = 1
	downBar = ShadyBar('Downloading...', max=total) # Progress bar
	for file in reversed(files):
		downBar.next()
		
		# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
		while True:
			try:
				pixelVals = list(Image.open(driveAPI.get_image_bytes_from_doc(driveAPI.get_service(), file)).convert('RGB').getdata())
			except:
				continue
			pixelVals = [j for i in pixelVals for j in i]
			if len(pixelVals) == 10224000:
				break
				
		pixelVals = array.array('B', pixelVals).tostring().rstrip(b'\x00')[:-1]
		
		# Write the data stored in "pixelVals" to the output file.
		result.write(pixelVals)
		count += 1

		# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
		gc.collect()
		
	result.close()
	downBar.finish()
	print('\nDownload complete!')
elif len(sys.argv) >= 3 and str(sys.argv[1]) == "delete":
	if len(sys.argv) == 4 and str(sys.argv[3]) == "force-delete":
		# Force delete confirms the deletion.
		delConfirm = True
	else:
		print('Please type "yes" (without quotes) to confirm your intent to delete this file.')
		print('Type any other value to abort the deletion. - ', end = '')
		if 'yes' == input(''):
			delConfirm = True

	# Repeatedly try deleting the folder until we succeed.
	if delConfirm:
		print('Deleting file.')
		while True:
			try:
				driveAPI.delete_file(driveAPI.get_service(), str(sys.argv[2]))
			except Exception as e:
				print('Deletion failed. Retrying.')
				print(e)
				continue
			break
		print('File deletion complete.')
	else:
		print('File deletion aborted.')
else:
	print_ascii_logo()
	print("help - Displays this help command.")
	print("upload <file path OR http/https URL> <optional: file name> - Uploads specified file to Google Drive")
	print("list - Lists the names of all InfiniDrive files and their IDs")
	print("download <file ID> <file path> - Downloads the contents of the specified file ID to the specified file path")
	print("delete <file ID> <optional flag: force-delete>- Deletes the InfiniDrive file specified by the given ID")
