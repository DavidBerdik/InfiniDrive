#!/usr/bin/python3

import os, shutil, sys, zipfile

from docs import begin_storage
from docs import download_docs
from docs import get_service
from docs import list_files
from docs import store_doc
from docx import Document
from PIL import Image
from subprocess import check_output

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
	
	# Iterate through file in 1MB (1048576 bytes) chunks.
	with open(str(sys.argv[2]), 'rb') as infile:
		# Read a 5MB chunk of data from the file.
		fileBytes = infile.read(1048575) # using 1 byte less than a full 1MB since it divides by 3 perfectly
		
		# Generate and save a temporary PNG.
		img = Image.frombytes('RGB', (len(fileBytes) // 3 // 25, 25), fileBytes)
		img.save('tmp.png')
		
		# Generate Word document with PNG in it and delete PNG
		doc = Document()
		doc.add_picture("tmp.png")
		doc.save(str(docNum) + ".docx")
		#os.remove("tmp.png")
		
		# Upload Word document to Google Drive and delete local copy
		#store_doc(driveConnect, dirId, str(docNum) + ".docx", str(sys.argv[2]))
		#os.remove(str(docNum) + ".docx")
		
		docNum = docNum + 1
elif len(sys.argv) == 2 and str(sys.argv[1]) == "list":
	list_files(get_service())
elif len(sys.argv) == 4 and str(sys.argv[1]) == "download":
	# Download all files from the Google Drive folder
	'''download_docs(get_service(), str(sys.argv[2]), "./dltemp")
    result_name = raw_input("Enter filename to save as: ")
    result = open("./dltemp/" + result_name, "wb")

    for filename in os.listdir("./dltemp"):
        # 	2.1.) For now, we are unzipping the temp docx but that will change once Steven's code is done.
        zipname = filename.replace("docx", "zip")
        dirname = zipname.replace("zip", "")
        bmpname = dirname + ".bmp"

        os.rename(filename, zipname)
        zipRef = zipfile.ZipFile(zipname, 'r')
        zipRef.extractall(dirname)
        zipRef.close()
        os.remove(zipname)
        #	2.2.) Convert the PNG back to BMP and save.
        Image.open("./" + dirname + "/word/media/image1.png").save(bmpname)
        #	2.3.) Delete the unzipped folder
        shutil.rmtree("./" + dirname)
        #	2.4.) Write the data stored in the BMP to the file we are downloading
        bfile = open(bmpname, "rb")
        bdata = bytearray(bfile.read())
        result.write(bdata[54:]
        bfile.close()
        #	2.5.) Delete the temporary BMP
        os.remove(bmpname)
        os.remove(dirname)

	result.close()'''
	print()
else:
	print("Error: Invalid command line arguments (use help to display help)")
