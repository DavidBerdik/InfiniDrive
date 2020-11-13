from libs.requirements import requirements

import array, gc, libs.drive_api as drive_api, libs.hash_handler as hash_handler, libs.upload_handler as upload_handler, math, os, requests, sys, threading

from libs.bar import getpatchedprogress
from libs.ftp_server import init_ftp_server
from libs.help import print_help
from PIL import Image
from progress.bar import ShadyBar
from progress.spinner import Spinner
from tabulate import tabulate

class InfiniDrive:
	def __init__(self):
		self.version = "1.0.22"
		self.progress = getpatchedprogress()

		if (len(sys.argv) == 3 or len(sys.argv) == 4) and str(sys.argv[1]) == "upload": self.upload()
		elif len(sys.argv) == 2 and str(sys.argv[1]) == "list": self.print_file_list()
		elif len(sys.argv) == 4 and str(sys.argv[1]) == "rename": self.rename()
		elif len(sys.argv) == 4 and str(sys.argv[1]) == "download": self.download()
		elif len(sys.argv) == 4 and str(sys.argv[1]) == "update": self.update()
		elif len(sys.argv) == 3 and str(sys.argv[1]) == "size": self.get_file_size()
		elif len(sys.argv) >= 3 and str(sys.argv[1]) == "delete": self.delete()
		elif len(sys.argv) == 5 and str(sys.argv[1]) == "ftp": init_ftp_server(str(sys.argv[2]), str(sys.argv[3]), int(sys.argv[4]))
		elif len(sys.argv) == 2 and str(sys.argv[1]) == "help": print_help(self.version)
		else: print("Invalid command. Please see the 'help' command for usage instructions.")

	def upload(self):
		# Get the name to use for the file.
		if len(sys.argv) == 3:
			# Use file path as name
			file_name = str(sys.argv[2])
		else:
			# Use user-specified name
			file_name = str(sys.argv[3])

		skip_new_dir_generation = False
		while drive_api.file_with_name_exists(drive_api.get_service(), file_name):
			ans = input('A file with the name "' + str(file_name) + '" already exists. Would you like to overwrite it? (y/n) - ').lower()
			if ans == 'y':
				skip_new_dir_generation = True
				break
			else:
				file_name = input("Please enter a new file name for this upload: ")

		# Create Google Drive folder
		if not skip_new_dir_generation:
			driveConnect, dirId = drive_api.begin_storage(file_name)

		# Hand off the upload process to the update function.
		self.update(file_name, str(sys.argv[2]))

	def print_file_list(self):
		filesList = drive_api.list_files(drive_api.get_service())
		if(len(filesList) == 0):
			print('No InfiniDrive uploads found')
		else:
			print(tabulate(filesList, headers=['Files'], tablefmt="psql"))

	def rename(self):
		try:
			drive_api.rename_file(drive_api.get_service(), str(sys.argv[2]), str(sys.argv[3]))
			print('File rename complete.')
		except Exception as e:
			print('An error occurred. Please report this issue on the InfiniDrive GitHub issue tracker and upload your "log.txt" file.')
			print('File rename failed.')

	def download(self):
		# Save file name from command line arguments.
		file_name = str(sys.argv[2])

		# Check if the file exists. If it does not, print an error message and return.
		if not drive_api.file_with_name_exists(drive_api.get_service(), file_name):
			print('File with name "' + file_name + '" does not exist.')
			return

		# Get Drive service.
		drive_service = drive_api.get_service()

		# Get a count of the number of fragments that make up the file.
		fragment_count = drive_api.get_fragment_count(drive_service, file_name)

		# For indexing fragments.
		fragment_index = 1

		# Get the InfiniDrive file ID from its name
		file_id = drive_api.get_file_id_from_name(drive_service, file_name)

		# Asynchronously retrieve a list of all files. We do this so that we can reduce Drive API calls, but if we wait for the list,
		# the FTP client will likely time out before we can finish, so we will retrieve one fragment at a time at first while the
		# entire list is retrieved in the background here.
		files = list()
		threading.Thread(target=drive_api.get_files_list_from_folder_async, args=(drive_api.get_service(), file_id, files)).start()

		# Open a file at the user-specified path to write the data to
		result = open(str(sys.argv[3]), "wb")

		# Download complete print flag
		showDownloadComplete = True

		# For all fragments...
		downBar = ShadyBar('Downloading...', max=fragment_count) # Progress bar
		while fragment_index <= fragment_count:
			downBar.next()

			# Get the fragment with the given index
			file = None
			if files == []:
				# The fragment list is not available yet, so retrieve one fragment.
				file = drive_api.get_files_with_name_from_folder(drive_service, file_id, str(fragment_index))[0]
			else:
				# The fragment list is available, so use it to locate the fragment.
				file = files[0][fragment_index - 1]

			# Get the RGB pixel values from the image as a list of tuples that we will break up and then convert to a bytestring.
			while True:
				try:
					pixelVals = list(Image.open(drive_api.get_image_bytes_from_doc(drive_api.get_service(), file)).convert('RGB').getdata())
				except Exception as e:
					continue
				pixelVals = [j for i in pixelVals for j in i]
				if len(pixelVals) == 10224000:
					break

			# If the downloaded values do not match the fragment hash, terminate download and report corruption.
			if hash_handler.is_download_invalid(file, bytearray(pixelVals)):
				downBar.finish()
				print("\nError: InfiniDrive has detected that the file upload on Google Drive is corrupted and the download cannot complete.", end="")
				showDownloadComplete = False
				break

			# Strip the null byte padding and "spacer byte" from pixelVals.
			pixelVals = array.array('B', pixelVals).tobytes().rstrip(b'\x00')[:-1]

			# Write the data stored in "pixelVals" to the output file.
			result.write(pixelVals)
			fragment_index += 1

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
			
		# Get Drive service.
		driveConnect = drive_api.get_service()
		
		# Check if a remote file with the given name exists. If one does not, print an error message and return.
		if not drive_api.file_with_name_exists(driveConnect, file_name):
			print('Remote file with name ' + file_name + ' does not exist.')
			return
		
		# Get directory ID.
		dirId = drive_api.get_file_id_from_name(driveConnect, file_name)
		
		# Get a list of the fragments that currently make up the file. If this is a new upload, it should come back empty.
		orig_fragments = drive_api.get_files_list_from_folder(driveConnect, dirId)

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
					upload_handler.handle_update_fragment(drive_api, orig_fragments[docNum-1], fileBytes, driveConnect, docNum)
				else:
					# Process the fragment and upload it to Google Drive.
					upload_handler.handle_upload_fragment(drive_api, fileBytes, driveConnect, dirId, docNum, failedFragmentsSet)

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
					upload_handler.handle_update_fragment(drive_api, orig_fragments[docNum-1], fileBytes, driveConnect, docNum)
				else:
					# Process the fragment and upload it to Google Drive.
					upload_handler.handle_upload_fragment(drive_api, fileBytes, driveConnect, dirId, docNum, failedFragmentsSet)

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
			drive_api.delete_file_by_id(drive_api.get_service(), orig_fragments[docNum]['id'])
			docNum = docNum + 1

		# Process fragment upload failures
		upload_handler.process_failed_fragments(drive_api, failedFragmentsSet, dirId)

		upBar.finish()

		# If the number of fragments to expect from a file upload is known, verify that the upload is not corrupted.
		if totalFrags != 'an unknown number of':
			print('Verifying upload.')
			foundFrags = len(drive_api.get_files_list_from_folder(drive_api.get_service(), dirId))
			if(totalFrags != foundFrags):
				print('InfiniDrive has detected that your upload was corrupted. Please report this issue on the InfiniDrive GitHub issue tracker and upload your "log.txt" file.')

		print('Upload complete!')

	def get_file_size(self, file_name=None):
		# Get the size of the given file.
		if file_name == None:
			file_name = str(sys.argv[2])

		while True:
			try:
				# Get the size of the given file
				file_size = drive_api.get_file_size(drive_api.get_service(), sys.argv[2])

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
					drive_api.delete_file(drive_api.get_service(), file_name)
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