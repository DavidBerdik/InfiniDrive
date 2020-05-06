class requirements:        
    def __init__(self):
        print("\nChecking Requirements...\n")
        if self.check_imports() and self.check_credentials():
            print("Requirements - Success\n\n\n")
            return
        quit()
    
    def check_imports(self):
        try:
            import array, gc, libs.driveAPI as driveAPI, math, os, requests, sys, time
            from binascii import crc32
            from io import BytesIO
            from libs.bar import getpatchedprogress
            from PIL import Image
            from progress.bar import ShadyBar
            from progress.spinner import Spinner
            from tabulate import tabulate
            from libs.uploadHandler import handle_upload_fragment
        except (ModuleNotFoundError, ImportError) as error:
            print("Oops! ", end = " ")
            print(error)
            print("To install all the libraries required by Infinidrive. If you use pip, execute one of the following commands from the root InfiniDrive directory:")
            print("1. pip install -r requirements.txt\n2. python -m pip install -r -requirements.txt")
            print("For more Information refer to Readme")
            return False
        return True

    def check_credentials(self):
        import os
        if not os.path.exists('credentials.json'):
            print('InfiniDrive could not start because you have not provided a "credentials.json" file.')
            print('Please do so and try again. Instructions for doing this are available in "README.md"')
            print('as well as online at https://github.com/DavidBerdik/InfiniDrive')
            return False
        elif not os.path.exists('token.pickle'):
            print("Please complete account authentication using the following URL.")
            print("You can then run your previous command again.\n")
            import libs.driveAPI as driveAPI
            driveAPI.get_service()
            return False
        return True

requirements()