import requests
from datetime import datetime

IMAGE_DL_PATH = "/home/pi/Documents/shouldibike/images/"
MIN_FILE_SIZE = 7000

class Image(object):
	def __init__(self, data):
		self.url, self.feedName, self.description = data
		self.localPath = ""
		self.isValid = False
		self.download()
	def download(self):
		try:
			download = requests.get(self.url, verify=False).content
			#Protection to skip corrupt images -- test it's at least like 7 KB or so
			if (len(download) >= MIN_FILE_SIZE):
				currentTime = datetime.now().strftime("%m-%d-%y_%H%M")
				self.localPath = IMAGE_DL_PATH + self.feedName  + "_" + currentTime + ".jpg"
				with open(self.localPath, 'wb') as dlWriter:
					dlWriter.write(download)
				self.isValid = True
			else:
				print("File was too small, skipping")
		except:
			print("Error downloading " + self.feedName)

