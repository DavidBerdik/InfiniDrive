import time

from binascii import crc32
from docx import Document
from io import BytesIO
from PIL import Image

# Handles uploading of a fragment of data to Google Drive.
def handle_upload_fragment(driveAPI, fileBytes, driveConnect, dirId, docNum, failedFragmentsSet, debug_log):
	# Add a "spacer byte" at the end to indciate end of data and start of padding.
	fileBytes += bytes([255])

	# Generate a new Word document.
	doc = Document()

	# Pad the fragment with enough null bytes to reach the requirements for the image dimensions.
	fileBytes += bytes(10224000 - len(fileBytes))
	
	# Calculate CRC32 hash for fileBytes
	hash = hex(crc32(fileBytes))

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
			driveAPI.store_doc(driveConnect, dirId, str(docNum) + ".docx", hash, mem_doc)
		except Exception as e:
			# If a fragment upload failure occurs, log the incident, add docNum to failedFragmentsSet,
			# and try again.
			debug_log.write("----------------------------------------\n")
			debug_log.write("Fragment upload failure. Fragment number is " + str(docNum) + ".\n")
			debug_log.write("Error:\n")
			debug_log.write(str(e) + "\n")
			failedFragmentsSet.add(docNum)
			continue
		break