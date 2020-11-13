import libs.hash_handler as hash_handler

from docx import Document
from io import BytesIO
from PIL import Image

# Handles uploading of a fragment of data to Google Drive.
def handle_upload_fragment(drive_api, fileBytes, driveConnect, dirId, docNum, failedFragmentsSet):
	# Pad fileBytes.
	fileBytes = pad_file_bytes(fileBytes)
	
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
			failedFragmentsSet.add(docNum)
			continue
		break

# Handles updating of a fragment of data to Google Drive.
def handle_update_fragment(drive_api, fragment, fileBytes, driveConnect, docNum):
	# Pad fileBytes.
	fileBytes = pad_file_bytes(fileBytes)

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
				continue
			break

def process_failed_fragments(drive_api, failed_fragments, dir_id):
	# For each document number in failed_fragments, check for duplicates and remove any if they are present.
	for name in failed_fragments:
		# Get duplicates.
		duplicates = drive_api.get_files_with_name_from_folder(drive_api.get_service(), dir_id, name)

		# For tracking if we should check data validity
		checkDataValidity = True

		# For each entry in the duplicates array...
		for file in duplicates:
			if checkDataValidity:
				# If we should check data validity, retrieve the file data and compare the hashes.
				fileData = bytearray([j for i in list(Image.open(drive_api.get_image_bytes_from_doc(drive_api.get_service(), file)).convert('RGB').getdata()) for j in i])
				
				# Get fragment hashes.
				crc32, sha256 = hash_handler.get_frag_hashes(file)

				if(crc32 == hash_handler.calc_crc32(fileData) and sha256 == hash_handler.calc_sha256(fileData)):
					# If the hashes are identical, mark for no further validity checks and do not delete the file.
					checkDataValidity = False
				else:
					# If the hashes do not match, delete the fragment.
					drive_api.delete_file_by_id(drive_api.get_service(), file['id'])
			else:
				# If we should not check data validity, delete the file.
				drive_api.delete_file_by_id(drive_api.get_service(), file['id'])

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

# Adds a "spacer byte" at the end of the given byte array to indciate the end of data and the start of padding, and pads
# the fragment with enough null bytes to reach the requirements for the image dimensions.
def pad_file_bytes(file_bytes):
	file_bytes += bytes([255])
	file_bytes += bytes(10224000 - len(file_bytes))
	return file_bytes