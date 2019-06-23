#!/usr/bin/python3

import array, driveAPI, gc, math, os, sys

from docx import Document
from io import BytesIO
from PIL import Image

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
	print("InfiniDrive v1.0.2 - An unlimited Google Drive storage solution")
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
elif len(sys.argv) == 3 and str(sys.argv[1]) == "upload":
	# Create Google Drive folder
	driveConnect, dirId = driveAPI.begin_storage(str(sys.argv[2]))
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
		driveAPI.store_doc(driveConnect, dirId, str(docNum) + ".docx", mem_doc)
	
		# Increment docNum for next Word document and read next chunk of data.
		docNum = docNum + 1
		fileBytes = infile.read(readChunkSizes)

		# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
		gc.collect()
	
	infile.close()
	print('Upload complete!')
	print('To download, use the following folder ID: ' + dirId)
			
elif len(sys.argv) == 2 and str(sys.argv[1]) == "list":
	driveAPI.list_files(driveAPI.get_service())
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
		pixelVals = list(Image.open(driveAPI.get_image_bytes_from_doc(driveAPI.get_service(), file)).convert('RGB').getdata())
		pixelVals = [j for i in pixelVals for j in i]
		pixelVals = array.array('B', pixelVals).tostring().rstrip(b'\x00')[:-1]
		
		# Write the data stored in "pixelVals" to the output file.
		result.write(pixelVals)
		count += 1

		# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
		gc.collect()
		
	result.close()
	print('Download complete!')
else:
	print_ascii_logo()
	print("help - Displays this help command.")
	print("upload <file path> - Uploads specified file to Google Drive")
	print("list - Lists the names of all Google Drive folders and their IDs")
	print("download <folder ID> <file path> - Downloads the contents of the specified folder ID to the specified file path\n")
