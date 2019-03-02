import os, shutil, sys, zipfile

from docx import Document
from PIL import Image
from docs import begin_storage
from docs import download_docs
from docs import get_service
from docs import store_doc

if len(sys.argv) == 2 and str(sys.argv[1]) == "help":
	print("Unlimited Google Drive Storage\n")
	print("help - Displays this help command.")
	print("upload <file path> - Uploads specified file to Google Drive")
	print("download <file path> - Downloads specified file to Google Drive")
elif len(sys.argv) == 3 and str(sys.argv[1]) == "upload":
	# 1.) Create Google Drive folder
	driveConnect, dirId = begin_storage(str(sys.argv[2]))
	# 2.) Get file byte size
	fileSize = os.path.getsize(sys.argv[2])
	# 3.) Loop through the file to read it and get bitmaps (waiting on Noah's C)
	#	3.1.) Get bitmap data and convert it to PNG saved on disk.
	Image.open("./testfiles/test-bitmap.bmp").save("tmp.png") # 3.2.) For now we are using "test-bitmap.bmp" but we will want to use Noah's data instead
	doc = Document() # 3.3.) Generate a Word document containing the PNG.
	doc.add_picture("tmp.png")
	doc.save("tmp.docx")
	os.remove("tmp.png") # 3.4.) Delete "tmp.png"
	# 3.5.) Upload Word document to Google Drive
	store_doc(driveConnect, dirId, "tmp.docx")
	os.remove("tmp.docx") # 3.6.) Delete the Word document
elif len(sys.argv) == 3 and str(sys.argv[1]) == "download":
	# 1.) Get file count in given folder in Google Drive (waiting on Steven)
	# 2.) Iterate through and download all docx files
	# 	2.1.) For now, we are unzipping the temp docx but that will change once Steven's code is done.
	os.rename("tmp.docx","tmp.zip")
	zipRef = zipfile.ZipFile("tmp.zip", 'r')
	zipRef.extractall("tmp")
	zipRef.close()
	os.remove("tmp.zip")
	#	2.2.) Convert the PNG back to BMP and save.
	Image.open("./tmp/word/media/image1.png").save("tmp.bmp")
	#	2.3.) Delete the unzipped folder
	shutil.rmtree("./tmp")
	#	2.4.) Write the data stored in the BMP to the file we are downloading
	#	2.5.) Delete the temporary BMP
	os.remove("tmp.bmp")
else:
	print("Error: Invalid command line arguments (use help to display help)")