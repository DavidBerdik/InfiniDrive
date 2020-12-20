from datetime import datetime
from rich import print

quota_strings = {
	True: ['Attention: As of June 1, 2021, Google counts Google Docs files towards the 15GB storage quota. Because',
			'this change prevents InfiniDrive from being able to upload files properly, uploading and updating files',
			'via the command line as well as uploading via the FTP interface is no longer possible. InfiniDrive can',
			'now only be used for renaming files, downloading files, querying for file sizes, and deleting files.'],
	False: ['Attention: On June 1, 2021, Google will begin counting Google Docs files towards the 15GB storage quota.',
			'This change will prevent InfiniDrive from being able to upload files properly. Because of this, uploading',
			'and updating files via the command line as well as uploading via the FTP interface will be disabled on',
			'that date. After this date is reached, InfiniDrive will only allow files to be renamed, downloaded,',
			'queried for size, and deleted.']
}

# Check if Google's new quota rules are being enforced. Return true if they are.
# More information: https://blog.google/products/photos/storage-policy-update/
def is_quota_enforced():
	return datetime.now() >= datetime(2021, 6, 1)

# Prints a quota alert to the terminal in red text
def print_quota_alert():
	for alert_frag in quota_strings[is_quota_enforced()]:
		print('[red bold]' + alert_frag + '[/]')
	print()

# Responds to the given FTP conn with the appropriate alert text.
def ftp_send_quota_alert(conn):
	for alert_frag in quota_strings[is_quota_enforced()]:
		conn.send(b'220-' + alert_frag.encode('UTF-8') + b'\r\n')
	conn.send(b'220 \r\n')