#!/usr/bin/python3

import array, docs, os, sys

from docx import Document
from io import BytesIO
from PIL import Image

if len(sys.argv) == 2 and str(sys.argv[1]) == "help":
	print("Unlimited Google Drive Storage\n")
	print("help - Displays this help command.")
	print("upload <file path> - Uploads specified file to Google Drive")
	print("list - Lists the names of all Google Drive folders and their IDs")
	print("download <folder ID> <file path> - Downloads the contents of the specified folder ID to the specified file path")
elif len(sys.argv) == 3 and str(sys.argv[1]) == "upload":
	# Create Google Drive folder
	driveConnect, dirId = docs.begin_storage(str(sys.argv[2]))
	
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
		docs.store_doc(driveConnect, dirId, str(docNum) + ".docx", mem_doc)
	
		# Increment docNum for next Word document and read next chunk of data.
		docNum = docNum + 1
		fileBytes = infile.read(readChunkSizes)
			
elif len(sys.argv) == 2 and str(sys.argv[1]) == "list":
	docs.list_files(docs.get_service())
elif len(sys.argv) == 4 and str(sys.argv[1]) == "download":
	# Get a list of the files in the given folder.
	files = docs.get_files_list_from_folder(docs.get_service(), str(sys.argv[2]))
	
	# Open a file at the user-specified path to write the data to
	result = open(str(sys.argv[3]), "wb")
	
	# For all files that are in the list...
	total = len(files)
	count = 1
	for file in reversed(files):
		print('Downloading file', count, 'of', total)
		
		# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
		pixelVals = list(Image.open(docs.get_image_bytes_from_doc(docs.get_service(), file)).convert('RGB').getdata())
		pixelVals = [j for i in pixelVals for j in i]
		pixelVals = array.array('B', pixelVals).tostring().rstrip(b'\x00')[:-1]
		
		# Write the data stored in "pixelVals" to the output file.
		result.write(pixelVals)
		count += 1
		
	result.close()
else:
	print("Error: Invalid command line arguments (use help to display help)")
