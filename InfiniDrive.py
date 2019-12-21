#!/usr/bin/python3

import array, driveAPI, gc, math, os, sys, time

from docx import Document
from io import BytesIO
from PIL import Image
from tabulate import tabulate

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
	print("InfiniDrive v1.0.7 - An unlimited Google Drive storage solution")
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
	
	# Create Google Drive folder
	driveConnect, dirId = driveAPI.begin_storage(file_name)
	totalFrags = math.ceil(os.stat(sys.argv[2]).st_size / 10223999)
	print('Upload started. Upload will be composed of ' + str(totalFrags) + ' fragments.')
	
	# Get file byte size
	fileSize = os.path.getsize(sys.argv[2])
	
	# Doc number
	docNum = 1
	
	# Iterate through file in 9.750365257263184MB (10223999 bytes) chunks.
	infile = open(str(sys.argv[2]), 'rb')
	
	# Read an initial 9.750365257263184MB chunk from the file.
	readChunkSizes = 10223999
	fileBytes = infile.read(readChunkSizes)
	
	# Keep looping until no more data is read.
	while fileBytes:
		print('Disassembling and uploading fragment ' + str(docNum) + ' of ' + str(totalFrags))

		# Add a "spacer byte" at the end to indciate end of data and start of padding.
		fileBytes += bytes([255])
	
		# Generate a new Word document.
		doc = Document()
		
		# Pad the fragment with enough null bytes to reach the requirements for the image dimensions.
		fileBytes += bytes(10224000 - len(fileBytes))
		
		# Generate and save a temporary PNG in memory.
		img = Image.frombytes('RGB', (2000, 1704), fileBytes)
		mem_img = BytesIO()
		img.save(mem_img, 'PNG')

		# Add temporary PNG to the Word document.
		doc.add_picture(mem_img)
		
		# Save the generated Word document.
		mem_doc = BytesIO()
		doc.save(mem_doc)
		
		# Upload Word document to Google Drive
		while True:
			try:
				driveAPI.store_doc(driveConnect, dirId, str(docNum) + ".docx", mem_doc)
			except:
				print('Fragment ' + str(docNum) + ' failed to upload. Retrying.')
				time.sleep(10) # Sleep for 10 seconds before checking for upload. This should hopefully prevent a race condition in which duplicates still occur.
				
				# Before reattempting the upload, check if the upload actually succeeded. If it did, delete it and redo it.
				while True:
					try:
						# Get the last file that was uploaded.
						last_file = driveAPI.get_last_file_upload_info(driveAPI.get_service(), dirId)
					except:
						# If querying for the last uploaded file fails, try again.
						continue
					
					if last_file == None or last_file['name'] != str(docNum):
						# No file uploads have taken place yet or the file name does not match the upload ID, so break without doing anything.
						break
					elif last_file['name'] == str(docNum):
						# The file name matches the upload ID, so delete the file.
						while True:
							try:
								time.sleep(10) # Sleep for 10 seconds for the same reason described earlier.
								driveAPI.delete_file(driveAPI.get_service(), last_file['id'])
								time.sleep(10) # Sleep for 10 seconds for the same reason described earlier.
								break
							except:
								continue
						break
				continue
			break
	
		# Increment docNum for next Word document and read next chunk of data.
		docNum = docNum + 1
		fileBytes = infile.read(readChunkSizes)

		# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
		gc.collect()
	
	infile.close()
	print('Upload complete!')
	print('To download, use the following folder ID: ' + dirId)
			
elif len(sys.argv) == 2 and str(sys.argv[1]) == "list":
	filesList = driveAPI.list_files(driveAPI.get_service())
	
	if(len(filesList) == 0):
		print('No InfiniDrive uploads found')
	else:
		print(tabulate(filesList, headers=['File Name', 'File ID']))
elif len(sys.argv) == 4 and str(sys.argv[1]) == "download":
	# Get a list of the files in the given folder.
	files = driveAPI.get_files_list_from_folder(driveAPI.get_service(), str(sys.argv[2]))
	
	# Open a file at the user-specified path to write the data to
	result = open(str(sys.argv[3]), "wb")
	
	# For all files that are in the list...
	total = len(files)
	count = 1
	for file in reversed(files):
		print('Downloading and reassembling fragment', count, 'of', total)
		
		# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
		while True:
			try:
				pixelVals = list(Image.open(driveAPI.get_image_bytes_from_doc(driveAPI.get_service(), file)).convert('RGB').getdata())
			except:
				print('Fragment ' + str(count) + ' failed to download. Retrying.')
				continue
			pixelVals = [j for i in pixelVals for j in i]
			if len(pixelVals) == 10224000:
				break
			else:
				print('Google Drive returned corrupted data for fragment ' + str(count) + '. Refetching.')
				
		pixelVals = array.array('B', pixelVals).tostring().rstrip(b'\x00')[:-1]
		
		# Write the data stored in "pixelVals" to the output file.
		result.write(pixelVals)
		count += 1

		# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
		gc.collect()
		
	result.close()
	print('Download complete!')
elif len(sys.argv) == 3 and str(sys.argv[1]) == "delete":
	# Repeatedly try deleting the folder until we succeed.
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
	print_ascii_logo()
	print("help - Displays this help command.")
	print("upload <file path> <optional: file name> - Uploads specified file to Google Drive")
	print("list - Lists the names of all InfiniDrive files and their IDs")
	print("download <file ID> <file path> - Downloads the contents of the specified file ID to the specified file path")
	print("delete <file ID> - Deletes the InfiniDrive file specified by the given ID")
