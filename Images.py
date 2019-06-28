import requests
from datetime import datetime

IMAGE_DL_PATH = "/home/pi/Documents/shouldibike/images/"

class Image(object):
    def __init__(self, url, feedName, description):
        self.url = url
        self.feedName = feedName
        self.localPath = ""
        self.description = description

class Images(object):
    def __init__(self, jobs, dlPath = 0):
        if (dlPath):
            self.dlPath = dlPath
        else:
            self.dlPath = IMAGE_DL_PATH
        self.downloadJobs = jobs
        self.download()
   
    def download(self):
        for images in self.downloadJobs:
            try:
                feedPull = requests.get(images.url).content
                currentTime = datetime.now().strftime("%m-%d-%y_%H%M")
                localPath = self.dlPath + images.feedName  + "_" + currentTime + ".jpg"
                with open(localPath, 'wb') as dlWriter:
                    dlWriter.write(feedPull)
                #what does this do?
                images.localPath = localPath
            except:
                print("Error downloading " + images.feedName)
