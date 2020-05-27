from libs.requirements import requirements

import array, gc, libs.driveAPI as driveAPI, math, os, requests, sys, time

from binascii import crc32
from hashlib import sha256
from io import BytesIO
from libs.bar import getpatchedprogress
from libs.help import print_help
from libs.uploadHandler import handle_update_fragment
from libs.uploadHandler import handle_upload_fragment
from PIL import Image
from progress.bar import ShadyBar
from progress.spinner import Spinner
from tabulate import tabulate

class InfiniDrive:
	def __init__(self):
		self.version = "1.0.19"
		self.debug_log = open("log.txt", "w")
		self.debug_log.write("Version: " + self.version + "\n\n")
		self.progress = getpatchedprogress()

		if (len(sys.argv) == 3 or len(sys.argv) == 4) and str(sys.argv[1]) == "upload": self.upload()
		elif len(sys.argv) == 2 and str(sys.argv[1]) == "list": self.print_file_list()
		elif len(sys.argv) == 4 and str(sys.argv[1]) == "rename": self.rename()
		elif len(sys.argv) == 4 and str(sys.argv[1]) == "download": self.download()
		elif len(sys.argv) == 4 and str(sys.argv[1]) == "update": self.update()
		elif len(sys.argv) == 3 and str(sys.argv[1]) == "size": self.get_file_size()
		elif len(sys.argv) >= 3 and str(sys.argv[1]) == "delete": self.delete()
		elif len(sys.argv) == 2 and str(sys.argv[1]) == "help": print_help(self.version)
		else: print("Invalid command. Please see the 'help' command for usage instructions.")

		self.debug_log.write("----------------------------------------\n")
		self.debug_log.write("Normal termination.")

	def upload(self):
		# Get the name to use for the file.
		if len(sys.argv) == 3:
			# Use file path as name
			file_name = str(sys.argv[2])
		else:
			# Use user-specified name
			file_name = str(sys.argv[3])

		skip_new_dir_generation = False
		while driveAPI.file_with_name_exists(driveAPI.get_service(), file_name):
			ans = input('A file with the name "' + str(file_name) + '" already exists. Would you like to overwrite it? (y/n) - ').lower()
			if ans == 'y':
				skip_new_dir_generation = True
				break
			else:
				file_name = input("Please enter a new file name for this upload: ")

		# Create Google Drive folder
		if not skip_new_dir_generation:
			driveConnect, dirId = driveAPI.begin_storage(file_name)

		# Hand off the upload process to the update function.
		self.update(file_name, str(sys.argv[2]))

	def print_file_list(self):
		filesList = driveAPI.list_files(driveAPI.get_service())
		if(len(filesList) == 0):
			print('No InfiniDrive uploads found')
		else:
			print(tabulate(filesList, headers=['Files'], tablefmt="psql"))

	def rename(self):
		try:
			driveAPI.rename_file(driveAPI.get_service(), str(sys.argv[2]), str(sys.argv[3]))
			print('File rename complete.')
		except Exception as e:
			self.debug_log.write("----------------------------------------\n")
			self.debug_log.write("File rename failure\n")
			self.debug_log.write("Old Name: " + str(sys.argv[2]) + "\n")
			self.debug_log.write("New Name: " + str(sys.argv[3]) + "\n")
			self.debug_log.write("Error:\n")
			self.debug_log.write(str(e) + "\n")
			print('An error occurred. Please report this issue on the InfiniDrive GitHub issue tracker and upload your "log.txt" file.')
			print('File rename failed.')

	def download(self):
		# Check if the file exists. If it does not, print an error message and return.
		if not driveAPI.file_with_name_exists(driveAPI.get_service(), sys.argv[2]):
			print('File with name "' + str(sys.argv[2]) + '" does not exist.')
			return
		
		# Get a list of the files in the given folder.
		files = driveAPI.get_files_list_from_folder(driveAPI.get_service(), driveAPI.get_file_id_from_name(driveAPI.get_service(), sys.argv[2]))

		# Open a file at the user-specified path to write the data to
		result = open(str(sys.argv[3]), "wb")

		# Download complete print flag
		showDownloadComplete = True

		# For all files that are in the list...
		total = len(files)
		count = 1
		downBar = ShadyBar('Downloading...', max=total) # Progress bar
		for file in reversed(files):
			downBar.next()

			# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
			while True:
				try:
					pixelVals = list(Image.open(driveAPI.get_image_bytes_from_doc(driveAPI.get_service(), file)).convert('RGB').getdata())
				except Exception as e:
					self.debug_log.write("----------------------------------------\n")
					self.debug_log.write("Fragment download failure\n")
					self.debug_log.write("Error:\n")
					self.debug_log.write(str(e) + "\n")
					continue
				pixelVals = [j for i in pixelVals for j in i]
				if len(pixelVals) == 10224000:
					break

			# Compare the hashes stored with document to the hashes of pixelVals. If they do not match, terminate download and report corruption.
			if('properties' in file and (file['properties']['crc32'] != hex(crc32(bytearray(pixelVals))) or
			  ('sha256' in file['properties'] and file['properties']['sha256'] != sha256(bytearray(pixelVals)).hexdigest()))):
				downBar.finish()
				print("\nError: InfiniDrive has detected that the file upload on Google Drive is corrupted and the download cannot complete.", end="")
				showDownloadComplete = False
				break

			pixelVals = array.array('B', pixelVals).tobytes().rstrip(b'\x00')[:-1]

			# Write the data stored in "pixelVals" to the output file.
			result.write(pixelVals)
			count += 1

			# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
			gc.collect()

		result.close()
		downBar.finish()
		if showDownloadComplete:
			print('\nDownload complete!')
	
	def update(self, file_name=None, file_path=None):
		# If no file name or file path is set, use the command line arguments.
		if file_name == None and file_path == None:
			file_name = sys.argv[2]
			file_path = sys.argv[3]
			
		# Get Drive service and directory ID.
		driveConnect = driveAPI.get_service()
		dirId = driveAPI.get_file_id_from_name(driveConnect, file_name)
		
		# Get a list of the fragments that currently make up the file. If this is a new upload, it should come back empty.
		orig_fragments = driveAPI.get_files_list_from_folder(driveConnect, dirId)
		orig_fragments.reverse()
		
		# Determine if upload is taking place from an HTTP or HTTPS URL.
		urlUpload = False
		if file_path[0:4].lower() == 'http':
			urlUpload = True
			urlUploadHandle = requests.get(file_path, stream=True, allow_redirects=True)

		fileSize = -1 # If file is being uploaded from web server and size cannot be retrieved this will stay at -1.
		if urlUpload:
			try:
				fileSize = int(urlUploadHandle.headers.get('content-length'))
			except TypeError:
				pass
			if fileSize == -1:
				# If fileSize is set to -1, set totalFrags to "an unknown number of"
				totalFrags = 'an unknown number of'
		else:
			fileSize = os.stat(file_path).st_size

		if fileSize != -1:
			totalFrags = math.ceil(fileSize / 10223999)
		print('Upload started. Upload will be composed of ' + str(totalFrags) + ' fragments.\n')

		# Set chunk size for reading files to 9.750365257263184MB (10223999 bytes)
		readChunkSizes = 10223999

		# Doc number
		docNum = 1

		# Used to keep track of the numbers for fragments that have failed uploads.
		failedFragmentsSet = set()

		# Progress bar
		if fileSize == -1:
			# The file size is unknown
			upBar = Spinner('Uploading... ')
		else:
			# The file size is known
			upBar = ShadyBar('Uploading...', max=max(math.ceil(fileSize / 10223999), len(orig_fragments)))

		if urlUpload:
			# If the upload is taking place from a URL...		
			# Iterate through remote file until no more data is read.
			for fileBytes in urlUploadHandle.iter_content(chunk_size=readChunkSizes):
				# Advance progress bar
				upBar.next()

				if docNum <= len(orig_fragments):
					# A remote fragment is present, so update it.
					# First, extract the hash value if present.
					currentHashCrc32 = ''
					currentHashSha256 = ''
					if 'properties' in orig_fragments[docNum-1]:
						currentHashCrc32 = orig_fragments[docNum-1]['properties']['crc32']
						if 'sha256' in orig_fragments[docNum-1]['properties']:
							currentHashSha256 = orig_fragments[docNum-1]['properties']['sha256']
					# Process update.
					handle_update_fragment(driveAPI, fileBytes, currentHashCrc32, currentHashSha256, driveConnect, orig_fragments[docNum-1]['id'], docNum, self.debug_log)
				else:
					# Process the fragment and upload it to Google Drive.
					handle_upload_fragment(driveAPI, fileBytes, driveConnect, dirId, docNum, failedFragmentsSet, self.debug_log)

				# Increment docNum for next Word document.
				docNum = docNum + 1

				# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
				gc.collect()
		else:
			# If the upload is taking place from a file path...	
			# Get file byte size
			fileSize = os.path.getsize(file_path)

			# Iterate through file in chunks.
			infile = open(str(file_path), 'rb')

			# Read an initial chunk from the file.
			fileBytes = infile.read(readChunkSizes)

			# Keep looping until no more data is read.
			while fileBytes:
				# Advance progress bar
				upBar.next()

				if docNum <= len(orig_fragments):
					# A remote fragment is present, so update it.
					# First, extract the hash value if present.
					currentHashCrc32 = ''
					currentHashSha256 = ''
					if 'properties' in orig_fragments[docNum-1]:
						currentHashCrc32 = orig_fragments[docNum-1]['properties']['crc32']
						if 'sha256' in orig_fragments[docNum-1]['properties']:
							currentHashSha256 = orig_fragments[docNum-1]['properties']['sha256']
					# Process update.
					handle_update_fragment(driveAPI, fileBytes, currentHashCrc32, currentHashSha256, driveConnect, orig_fragments[docNum-1]['id'], docNum, self.debug_log)
				else:
					# Process the fragment and upload it to Google Drive.
					handle_upload_fragment(driveAPI, fileBytes, driveConnect, dirId, docNum, failedFragmentsSet, self.debug_log)

				# Increment docNum for next Word document and read next chunk of data.
				docNum = docNum + 1
				fileBytes = infile.read(readChunkSizes)

				# Run garbage collection. Hopefully, this will prevent process terminations by the operating system on memory-limited devices such as the Raspberry Pi.
				gc.collect()

			infile.close()
		
		# If an update took place and the new file had fewer fragments than the previous file, delete any leftover fragments from the previous upload.
		docNum = docNum - 1
		while docNum < len(orig_fragments):
			upBar.next()
			driveAPI.delete_file_by_id(driveAPI.get_service(), orig_fragments[docNum]['id'])
			docNum = docNum + 1

		# For each document number in failedFragmentsSet, check for duplicates and remove any if they are present.
		self.debug_log.write("----------------------------------------\n")
		self.debug_log.write("Processing detected corruption...\n")
		for name in failedFragmentsSet:
			# Get duplicates.
			duplicates = driveAPI.get_files_with_name_from_folder(driveAPI.get_service(), dirId, name)
			self.debug_log.write("	Processing corruption of fragments with name " + str(name) + "\n")

			# For tracking if we should check data validity
			checkDataValidity = True

			# For each entry in the duplicates array...
			for file in duplicates:
				if checkDataValidity:
					# If we should check data validity, retrieve the file data and compare the hashes.
					fileData = bytearray([j for i in list(Image.open(driveAPI.get_image_bytes_from_doc(driveAPI.get_service(), file)).convert('RGB').getdata()) for j in i])

					if(file['properties']['crc32'] == hex(crc32(fileData)) and file['properties']['sha256'] == sha256(fileBytes).hexdigest()):
						# If the hashes are identical, mark for no further validity checks and do not delete the file.
						checkDataValidity = False
						self.debug_log.write("		Validity check disabled\n")
					else:
						# If the hashes do not match, delete the fragment.
						driveAPI.delete_file(driveAPI.get_service(), file['id'])
						self.debug_log.write("		Removed corrupt duplicate with ID " + file['id'] + " | checkDataValidity = True\n")
				else:
					# If we should not check data validity, delete the file.
					driveAPI.delete_file(driveAPI.get_service(), file['id'])
					self.debug_log.write("		Removed corrupt duplicate with ID " + file['id'] + " | checkDataValidity = False\n")

		self.debug_log.write("Processing of detected corruption completed.\n")

		upBar.finish()

		# If the number of fragments to expect from a file upload is known, verify that the upload is not corrupted.
		if totalFrags != 'an unknown number of':
			print('Verifying upload.')
			foundFrags = len(driveAPI.get_files_list_from_folder(driveAPI.get_service(), dirId))
			if(totalFrags != foundFrags):
				self.debug_log.write("----------------------------------------\n")
				self.debug_log.write("InfiniDrive detected upload corruption.\n")
				self.debug_log.write("Expected Fragments: " + str(totalFrags) + "\n")
				self.debug_log.write("Actual Fragments  : " + str(foundFrags) + "\n")
				print('InfiniDrive has detected that your upload was corrupted. Please report this issue on the InfiniDrive GitHub issue tracker and upload your "log.txt" file.')

		print('Upload complete!')

	def get_file_size(self, file_name=None):
		# Get the size of the given file.
		if file_name == None:
			file_name = str(sys.argv[2])

		while True:
			try:
				# Get a list of the files in the given folder.
				files = driveAPI.get_files_list_from_folder(driveAPI.get_service(), driveAPI.get_file_id_from_name(driveAPI.get_service(), sys.argv[2]))
				
				# Get the bytes from the last fragment.
				last_frag_bytes_len = len(array.array('B', [j for i in list(Image.open(driveAPI.get_image_bytes_from_doc(driveAPI.get_service(), files[0])).convert('RGB').getdata()) for j in i]) \
					.tobytes().rstrip(b'\x00')[:-1])
				
				# Calculate the number of bytes that make up the file.
				file_size = ((len(files) - 1) * 10223999) + last_frag_bytes_len
				
				# Print the appropriate sizes.
				print(sys.argv[2] + " File Size")
				if file_size >= 1125899906842624: print(file_size / 1125899906842624, "Petabytes")
				if file_size >= 1099511627776: print(file_size / 1099511627776, "Terabytes")
				if file_size >= 1073741824: print(file_size / 1073741824, "Gigabytes")
				if file_size >= 1048576: print(file_size / 1048576, "Megabytes")
				if file_size >= 1024: print(file_size / 1024, "Kilobytes")
				print(file_size, "bytes")
				break
			except Exception as e:
				if(str(e)[:14] == "<HttpError 404"):
						print('File with name ' + str(sys.argv[2]) + ' does not exist.')
						break
				print(e)
				print('File size listing failed. Retrying.')
				continue

	def delete(self, file_name=None, silent_delete=False):
		if file_name != None:
			delConfirm = True
		else:	
			file_name = str(sys.argv[2])
			delConfirm = False
			if len(sys.argv) == 4 and str(sys.argv[3]) == "force-delete":
					# Force delete confirms the deletion.
					delConfirm = True
			else:
				print('Please type "yes" (without quotes) to confirm your intent to delete this file.')
				print('Type any other value to abort the deletion. - ', end = '')
				if 'yes' == input(''):
					delConfirm = True

		# Repeatedly try deleting the folder until we succeed.
		if delConfirm:
			if not silent_delete:
				print('Deleting file.')
			while True:
				try:
					driveAPI.delete_file(driveAPI.get_service(), file_name)
				except Exception as e:
					if(str(e)[:14] == "<HttpError 404"):
						if not silent_delete:
							print('File with name ' + str(sys.argv[2]) + ' does not exist.')
						break
					if not silent_delete:
						print(e)
						print('Deletion failed. Retrying.')
					continue
				else:
					if not silent_delete:
						print('File deletion complete.')
					break
		else:
			print('File deletion aborted.')

InfiniDrive()