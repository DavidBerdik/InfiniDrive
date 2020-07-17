import libs.drive_api as drive_api, PySimpleGUI as ui
import time

class UI:
	files_list = ui.Listbox(values=['Loading file list...'], font=('Arial', 12), size=(70, 10))

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
			[self.files_list],
			[ui.Button('Upload', font=('Arial', 16)), ui.Button('Download', font=('Arial', 16)), ui.Button('Update', font=('Arial', 16)),
				ui.Button('Rename', font=('Arial', 16)), ui.Button('Size', font=('Arial', 16)), ui.Button('Delete', font=('Arial', 16))]
		]

		# Create window
		window = ui.Window('InfiniDrive v' + version, main_layout, finalize='True')

		# Load file list
		self.load_files_list()

		# Window event loop
		while True:
			event, values = window.read()

			# Break the event loop if the user clicks the close button
			if event == ui.WIN_CLOSED:
				break

		window.close()
	
	def load_files_list(self):
		# Load the list of files
		self.files_list.Update(values=[file for files in drive_api.list_files(drive_api.get_service()) for file in files])