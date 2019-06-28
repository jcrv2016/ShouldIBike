import urllib.request, xml.etree.ElementTree as ET
class Subway(object):
    def __init__(self):
        self.url = "http://web.mta.info/status/serviceStatus.txt"
        self.apiUp = False
        self.delays = []
        self.goodService = []
        self.plannedWork = []
        self.serviceChange = []
        self.text = ""
        self.pullData()
    def pullData(self):
        try:
            response = urllib.request.urlopen(self.url)
            tree = ET.parse(response)
            root = tree.getroot()  
            for x in range(0,10):
                if("GOOD SERVICE" in (root[2][x][1].text)):
                    self.goodService.append(str(root[2][x][0].text))
                elif("PLANNED WORK" in (root[2][x][1].text)):
                    self.plannedWork.append(str(root[2][x][0].text))
                elif("DELAYS" in (root[2][x][1].text)):
                    self.delays.append(str(root[2][x][0].text))
                elif("SERVICE CHANGE" in (root[2][x][1].text)):
                    self.serviceChange.append(str(root[2][x][0].text))
            self.apiUp = True
        except:
            self.apiUp = False
    def printStatus(self):
        def interpret(keyword, string):
            if (keyword):
                self.text += string + ":"
                max = len(keyword) -1
                for index, f in enumerate(keyword):
                    self.text += f
                    if(index != max):
                        self.text += "/"
                    else:
                        self.text += ". "           
        if(self.apiUp):
            self.text += "\nMTA: "
            interpret(self.delays, "Delays")
            interpret(self.plannedWork, "Track Work")
            interpret(self.serviceChange, "Service Change")
            interpret(self.goodService, "Good Service")
            #MTA API still doesn't mention W train, so I am field-correcting NQR to NQRW
            self.text = self.text.replace("NQR", "NQRW")
        return self.text
