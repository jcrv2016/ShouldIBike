from credentials import *
import urllib.request
import xml.etree.ElementTree as ET
class RoadConditions(object):
    def __init__(self):
        self.url = "https://511ny.org/api/getwinterroadconditions?key=" + NY511_KEY + "&format=xml"
        self.wet = False
        self.snowy = False
        self.text = ""
        self.apiUp = False
        self.pullData()
    def pullData(self):
        try:
            response = urllib.request.urlopen(self.url)
            tree = ET.parse(response)
            root = tree.getroot()
             
            for item in root:
                if "NYC" in item[1].text:
                    self.apiUp = True
                    if ("Wet" in item[0].text):
                        self.wet = True
                        break
                    if ("Snow" in item[0].text):
                        self.snowy = True
                        break
            self.text = "\nMajor Roads: Currently "
            if(self.wet and self.snowy):
                self.text += "wet/snow/ice"
            elif(self.wet):
                self.text += "wet"
            elif(self.snowy):
                self.text += "snow/ice"
            else:
                self.text += "dry"
        except:
            self.wet = None
            self.snowy = None
            self.text = ""
            
