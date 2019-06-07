#!/usr/bin/python3

import array, os, shutil, sys, zipfile

from docs import begin_storage
from docs import download_docs
from docs import get_service
from docs import list_files
from docs import store_doc
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
	driveConnect, dirId = begin_storage(str(sys.argv[2]))
	
	# Get file byte size
	fileSize = os.path.getsize(sys.argv[2])
	
	# Doc number
	docNum = 1
	
	# Iterate through file in 9.75MB (10223616 bytes) chunks.
	infile = open(str(sys.argv[2]), 'rb')
	
	# Read an initial 9.75MB chunk from the file.
	readChunkSizes = 10223616
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
		img = Image.frombytes('RGBA', (2000, 1278), fileBytes)
		mem_img = BytesIO()
		img.save(mem_img, 'PNG')

		# Add temporary PNG to the Word document.
		doc.add_picture(mem_img)
		
		# Save the generated Word document.
		mem_doc = BytesIO()
		doc.save(mem_doc)
		
		# Upload Word document to Google Drive
		store_doc(driveConnect, dirId, str(docNum) + ".docx", mem_doc)
	
		# Increment docNum for next Word document and read next chunk of data.
		docNum = docNum + 1
		fileBytes = infile.read(readChunkSizes)
			
elif len(sys.argv) == 2 and str(sys.argv[1]) == "list":
	list_files(get_service())
elif len(sys.argv) == 4 and str(sys.argv[1]) == "download":
	# Download all files from the Google Drive folder
	download_docs(get_service(), str(sys.argv[2]), "./dltemp")
	result = open(str(sys.argv[3]), "wb")

	# For all Word documents that were downloaded from Google Drive...
	for filenum in range(1, len(os.listdir("./dltemp")) + 1):
		filename = str(filenum) + ".docx"
		# Extract the Word document from which we will read the images.
		dirname = filename.replace(".docx", "")
		zipRef = zipfile.ZipFile("./dltemp/" + filename, 'r')
		zipRef.extractall("./dltemp/" + dirname)
		zipRef.close()
		os.remove("./dltemp/" + filename)
		
		# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
		pixelVals = list(Image.open("./dltemp/" + dirname + "/word/media/image1.png").convert('RGBA').getdata())
		pixelVals = [j for i in pixelVals for j in i]
		pixelVals = array.array('B', pixelVals).tostring().rstrip(b'\x00')[:-1]
		
		# Write the data stored in "pixelVals" to the output file.
		result.write(pixelVals)
		
		# Delete the unzipped folder
		shutil.rmtree("./dltemp/" + dirname)
		
	# Delete the "dltemp" folder and close the file we wrote to.
	shutil.rmtree("./dltemp")
	result.close()
else:
	print("Error: Invalid command line arguments (use help to display help)")
