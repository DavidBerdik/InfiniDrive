import time

from docx import Document
from io import BytesIO
from PIL import Image

# Handles uploading of a fragment of data to Google Drive.
def handle_upload_fragment(driveAPI, fileBytes, driveConnect, dirId, docNum, debug_log):
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
		except Exception as e:
			debug_log.write("----------------------------------------\n")
			debug_log.write("Fragment upload failure\n")
			debug_log.write("Error:\n")
			debug_log.write(str(e) + "\n")
			
			time.sleep(10) # Sleep for 10 seconds before checking for upload. This should hopefully prevent a race condition in which duplicates still occur.
			
			# Before reattempting the upload, check if the upload actually succeeded. If it did, delete it and redo it.
			while True:
				try:
					# Get the last file that was uploaded.
					last_file = driveAPI.get_last_file_upload_info(driveAPI.get_service(), dirId)
				except Exception as e:
					# If querying for the last uploaded file fails, try again.
					debug_log.write("	Nested failure - failure to query for last uploaded file\n")
					debug_log.write("	Error:\n")
					debug_log.write("	" + str(e) + "\n")
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
						except Exception as e:
							debug_log.write("	Nested failure - failure to delete corrupted bad upload\n")
							debug_log.write("	Error:\n")
							debug_log.write("	" + str(e) + "\n")
							continue
					break
			continue
		break