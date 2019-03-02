from docx import Document
import os
import zipfile

def writeWord(imgPath, wordPath):
	# Write a word document to wordPath with the image
	# imgPath in it.
	doc = Document()
	doc.add_picture(imgPath)
	doc.save(wordPath)

def readPngFromWord(wordPath):
	# FOR NOW THE IMAGE IS NOT READ. THE WORD DOC IS JUST EXTRACTED.
	# THIS WILL CHANGE.
	# "Read" a word document to extract the image from it.
	nameTo = wordPath.replace('.docx', '.zip')
	extractDir = wordPath.replace('.docx', '')
	zipRef = zipfile.ZipFile(wordPath, 'r')
	zipRef.extractall(extractDir)
	zipRef.close()
	os.remove(nameTo)
	#os.rmdir(extractDir) - for now we do not want to remove the extracted directory. will do later.