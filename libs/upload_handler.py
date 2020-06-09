import libs.hash_handler as hash_handler

from docx import Document
from io import BytesIO
from PIL import Image

# Handles uploading of a fragment of data to Google Drive.
def handle_upload_fragment(drive_api, fileBytes, driveConnect, dirId, docNum, failedFragmentsSet, debug_log):
	# Add a "spacer byte" at the end to indciate end of data and start of padding and pad the fragment with
	# enough null bytes to reach the requirements for the image dimensions.
	fileBytes += bytes([255])
	fileBytes += bytes(10224000 - len(fileBytes))
	
	# Calculate CRC32 and SHA256 hashes for fileBytes
	hash_crc32, hash_sha256 = hash_handler.calc_hashes(fileBytes)

	# Generate a new Word document
	mem_doc = generate_word_doc(fileBytes)

	# Upload Word document to Google Drive
	while True:
		try:
			drive_api.store_doc(driveConnect, dirId, str(docNum) + ".docx", hash_crc32, hash_sha256, mem_doc)
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

# Handles updating of a fragment of data to Google Drive.
def handle_update_fragment(drive_api, fragment, fileBytes, driveConnect, docNum, debug_log):
	# Add a "spacer byte" at the end to indciate end of data and start of padding and pad the fragment with
	# enough null bytes to reach the requirements for the image dimensions.
	fileBytes += bytes([255])
	fileBytes += bytes(10224000 - len(fileBytes))

	# Get the fragment ID.
	fragId = fragment['id']

	# Get the CRC32 and SHA256 hashes for the current state of the fragment.
	currentHashCrc32, currentHashSha256 = hash_handler.get_frag_hashes(fragment)

	# Calculate CRC32 and SHA256 hashes for fileBytes
	hash_crc32, hash_sha256 = hash_handler.calc_hashes(fileBytes)

	# Check if the hashes for the fragment in its current state is the same as the new fragment's hash. If they are not
	# the same, then update the fragment. If they are the same, then there is nothing to do.
	if hash_crc32 != currentHashCrc32 or hash_sha256 != currentHashSha256:
		# Generate a new Word document
		mem_doc = generate_word_doc(fileBytes)

		# Upload replacement Word document to Google Drive
		while True:
			try:
				drive_api.update_fragment(driveConnect, fragId, hash_crc32, hash_sha256, mem_doc)
			except Exception as e:
				# If a fragment upload failure occurs, log the incident and try again.
				debug_log.write("----------------------------------------\n")
				debug_log.write("Fragment upload failure. Fragment number is " + str(docNum) + ".\n")
				debug_log.write("Error:\n")
				debug_log.write(str(e) + "\n")
				continue
			break

# Generates a Word document containing the fragment, saves the document to a BytesIO object, and returns the object.
def generate_word_doc(fileBytes):
	# Generate a new Word document.
	doc = Document()

	# Generate and save a temporary PNG in memory.
	img = Image.frombytes('RGB', (2000, 1704), fileBytes)
	mem_img = BytesIO()
	img.save(mem_img, 'PNG')

	# Add temporary PNG to the Word document.
	doc.add_picture(mem_img)

	# Save the generated Word document.
	mem_doc = BytesIO()
	doc.save(mem_doc)
	
	# Return the BytesIO object that stores the document.
	return mem_doc