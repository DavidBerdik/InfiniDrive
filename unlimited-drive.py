import sys

if len(sys.argv) == 2 and str(sys.argv[1]) == "help":
	print("Unlimited Google Drive Storage\n")
	print("help - Displays this help command.")
	print("upload <file path> - Uploads specified file to Google Drive")
	print("download <file path> - Downloads specified file to Google Drive")
elif len(sys.argv) == 3 and str(sys.argv[1]) == "download":
	# Download code goes here.
	print("Download here")
elif len(sys.argv) == 3 and str(sys.argv[1]) == "upload":
	# Upload code goes here.
	print("Upload here")
else:
	print("Error: Invalid command line arguments (use help to display help)")