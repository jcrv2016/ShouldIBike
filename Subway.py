import urllib.request, xml.etree.ElementTree as ET
class Subway(object):
    def __init__(self):
        self.url = "http://web.mta.info/status/serviceStatus.txt"
        self.apiUp = False
        self.delays = []
        self.goodService = []
        self.plannedWork = []
        self.serviceChange = []
        self.noScheduledService = []
        self.essentialService = []
        self.detours = []
        self.partSuspended = []
        self.slowSpeeds = []
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
                elif("NO SCHEDULED SERVICE" in (root[2][x][1].text)):
                    self.noScheduledService.append(str(root[2][x][0].text))
                elif("ESSENTIAL SERVICE" in (root[2][x][1].text)):
                    self.essentialService.append(str(root[2][x][0].text))
                elif("SLOW SPEEDS" in (root[2][x][1].text)):
                    self.slowSpeeds.append(str(root[2][x][0].text))
                elif("PART SUSPENDED" in (root[2][x][1].text)):
                    self.partSuspended.append(str(root[2][x][0].text))
                elif("DETOURS" in (root[2][x][1].text)):
                    self.detours.append(str(root[2][x][0].text))
                
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
            interpret(self.serviceChange, "Svc Change")
            interpret(self.goodService, "Good Svc")
            interpret(self.noScheduledService, "No Svc-Certain Lines")
            interpret(self.essentialService, "Essential Svc")
            interpret(self.detours, "Detours")
            interpret(self.partSuspended, "Part Suspended")
            interpret(self.slowSpeeds, "Slow Speeds")
            #MTA API still doesn't mention W train, so I am field-correcting NQR to NQRW
            self.text = self.text.replace("NQR", "NQRW")
        return self.text
