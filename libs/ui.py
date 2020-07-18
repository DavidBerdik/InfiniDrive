import asyncio, libs.drive_api as drive_api, PySimpleGUI as ui

# Execute a function in the background without waiting for it to complete. Based on https://stackoverflow.com/a/53255955/2941352
def background_exec_no_wait(func):
	def wrapped(*args, **kwargs):
		return asyncio.get_event_loop().run_in_executor(None, func, *args, *kwargs)
	return wrapped

class UI:
	window = None

	def __init__(self, version):
		# Define theme
		ui.LOOK_AND_FEEL_TABLE['infinidrive_ui'] = {
			'BACKGROUND': 'white',
			'TEXT': '#323232',
			'INPUT': '#DFE2E8',
			'TEXT_INPUT': '#000000',
			'SCROLL': '#C7E78B',
			'BUTTON': ('white', '#505050'),
			'PROGRESS': ('white', 'black'),
			'BORDER': 0, 'SLIDER_DEPTH': 0, 'PROGRESS_DEPTH': 0,
		}
		ui.theme('infinidrive_ui')

		# Define main window layout
		main_layout = [
			[ui.Text('InfiniDrive v' + version, font=('Arial', 24))],
			[ui.Text('Files:', font=('Arial', 20))],
			[ui.Listbox(values=['Loading file list...'], font=('Arial', 12), size=(70, 10), key='files_list')],
			[ui.Button('Upload', font=('Arial', 16), disabled=True, key='btn_up'), ui.Button('Download', font=('Arial', 16), disabled=True, key='btn_down'),
				ui.Button('Update', font=('Arial', 16), disabled=True, key='btn_update'), ui.Button('Rename', font=('Arial', 16), disabled=True, key='btn_rename'),
				ui.Button('Size', font=('Arial', 16), disabled=True, key='btn_size'), ui.Button('Delete', font=('Arial', 16), disabled=True, key='btn_delete')]
		]

		# Create window
		self.window = ui.Window('InfiniDrive v' + version, main_layout, finalize='True')

		# Load file list
		self.load_files_list()

		# Window event loop
		while True:
			event, values = self.window.read()

			if event == ui.WIN_CLOSED:
				# Break the event loop if the user clicks the close button
				break
			elif event == 'btn_up':
				# Handle upload event
				pass
			elif event == 'btn_down':
				# Handle download event
				pass
			elif event == 'btn_update':
				# Handle update event
				pass
			elif event == 'btn_rename':
				# Handle rename event
				pass
			elif event == 'btn_size':
				# Handle size event
				pass
			elif event == 'btn_delete':
				# Handle delete event
				pass

		self.window.close()

	# Asynchronously execute a load of the file list
	@background_exec_no_wait
	def load_files_list(self):
		# Load the list of files
		self.window.FindElement('files_list').Update(values=[file for files in drive_api.list_files(drive_api.get_service()) for file in files])
		self.set_main_btns_enabled(True)

	# Toggles the usage states of the main user interface buttons
	def set_main_btns_enabled(self, enabled):
		button_keys = ['btn_up', 'btn_down', 'btn_update', 'btn_rename', 'btn_size', 'btn_delete']
		for key in button_keys:
			self.window.FindElement(key).Update(disabled=not enabled)