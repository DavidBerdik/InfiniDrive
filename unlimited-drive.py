#!/usr/bin/python3

import array, funcy, os, shutil, sys, zipfile

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
	
	# Iterate through file in 48MB (50331648 bytes) chunks.
	infile = open(str(sys.argv[2]), 'rb')
	
	# Read an initial 48MB chunk from the file.
	readChunkSizes = 50331648
	fileBytes = infile.read(readChunkSizes)
	
	# Keep looping until no more data is read.
	while fileBytes:
		# Split the 48MB chunk to a list of 16000000 byte fragments.
		chunkSizes = 16000000
		byteFrags = list(funcy.chunks(chunkSizes, fileBytes))
		
		# Generate a new Word document.
		doc = Document()
		
		# Iterate through byteFrags one fragment at a time.
		for byteFrag in byteFrags:
			# If byteFrag is not exactly the correct size, pad it will null bytes.
			if len(byteFrag) < chunkSizes:
				byteFrag += bytes(chunkSizes - len(byteFrag))
		
			# Generate and save a temporary PNG in memory.
			img = Image.frombytes('RGBA', (2000, 2000), byteFrag)
			mem_img = BytesIO()
			img.save(mem_img, 'PNG')
			
			# Add temporary PNG to the Word document.
			doc.add_picture(mem_img)
		
		# Save the generated Word document.
		doc.save(str(docNum) + ".docx")
		
		# Upload Word document to Google Drive and delete local copy
		store_doc(driveConnect, dirId, str(docNum) + ".docx", str(docNum) + ".docx")
		os.remove(str(docNum) + ".docx")
	
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
	for filename in os.listdir("./dltemp"):
		# Extract the Word document from which we will read the images.
		zipname = filename.replace("docx", "zip")
		dirname = zipname.replace(".zip", "")
		os.rename("./dltemp/" + filename, "./dltemp/" + zipname)
		zipRef = zipfile.ZipFile("./dltemp/" + zipname, 'r')
		zipRef.extractall("./dltemp/" + dirname)
		zipRef.close()
		os.remove("./dltemp/" + zipname)
		
		# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
		pixelVals = list(Image.open("./dltemp/" + dirname + "/word/media/image1.png").convert('RGBA').getdata())
		pixelVals = [j for i in pixelVals for j in i]
		pixelVals = array.array('B', pixelVals).tostring().rstrip(b'\x00')
		
		# Write the data stored in "pixelVals" to the output file.
		result.write(pixelVals)
		
		# Delete the unzipped folder
		shutil.rmtree("./dltemp/" + dirname)
		
		# Delete the "dltemp" folder.
		shutil.rmtree("./dltemp")

		#result.close()
		print()
else:
	print("Error: Invalid command line arguments (use help to display help)")
