from libs.time_bomb import is_quota_enforced

def print_help(version):
	print("\n            ,,,                         ,,,")
	print("      &@@@@@@@@@@@@@              @@@@@@@@@@@@@@")
	print("    @@@@@@@#    %@@@@@#        @@@@@@@@@@@@@@@@@@@@")
	print("  @@@@@@            #@@@     &@@@@@@@         @@@@@@")
	print(" @@@@@                @@@@  @@@@@@@             @@@@@")
	print(" @@@@                   @@@@@@@@@                @@@@@")
	print("@@@@@                    @@@@@@@                  @@@@")
	print("@@@@@                    @@@@@@                   @@@@#")
	print("@@@@@                   @@@@@@                    @@@@,")
	print("&@@@@                 &@@@@@@@@                  *@@@@")
	print(" @@@@@               @@@@@@@ @@@                 @@@@@")
	print("  @@@@@            *@@@@@@#   @@@               @@@@@")
	print("   @@@@@@#       @@@@@@@@      @@@@#          @@@@@@")
	print("    *@@@@@@@@@@@@@@@@@@          @@@@@@@@%@@@@@@@@")
	print("       #@@@@@@@@@@@@               *@@@@@@@@@@@*\n")
	print("InfiniDrive v" + version + " - An unlimited Google Drive storage solution")
	print("By David Berdik, Steven Myrick, Noah Greenberg, and Maitree Rawat\n")
	print(">> help - Displays this help command.")
	if not is_quota_enforced(): print(">> upload <file path OR http/https URL> <optional: file name> - Uploads specified file to Google Drive")
	print(">> list - Lists the names of all InfiniDrive files")
	print(">> rename <current file name> <new file name> - Renames the file with the specified name to the specified new name")
	print(">> download <file name> <file path> - Downloads the contents of the specified file name to the specified file path")
	if not is_quota_enforced(): print(">> update <remote file name> <file path OR http/https URL> - Updates the specified remote file with the file located at the specified path")
	print(">> size <file name> - Lists the size of the specified InfiniDrive file")
	print(">> delete <file name> <optional flag: force-delete> - Deletes the specified InfiniDrive file")
	print(">> ftp <username> <password> <port> - Starts the InfiniDrive FTP server with the given username, password, and port number")