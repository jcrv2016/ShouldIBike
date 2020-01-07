class Recommendation(object):
    def __init__(self, weatherObj):
        self.weatherObj = weatherObj
        self.rating = ""
        self.rating2 = ""
        self.weatherEmoji = ""
        self.attire = ""
        self.weatherObj.update()
        self.makeRecommendation()
        self.recommendAttire()
    
    def makeRecommendation(self):
        # this could be a more maintainable and readable lookup matrix somehow
        if (self.weatherObj.snow):
            self.rating = "POOR"
            if (self.weatherObj.rain):
                self.rating2 = "; Be prepared for snow/rain"
            else:
                self.rating2 = "; Be prepared for snow"
            self.weatherEmoji = "⛄❄️"
        elif (self.weatherObj.snowy):
            self.rating = "POOR"
            self.rating2 = "; Roads are likely messy"
            self.weatherEmoji = "⛄❄️"
        elif (self.weatherObj.weatherStatus in ["extreme weather"]):
            self.rating = "POOR"
            self.weatherEmoji = "⚡❕"
        elif (self.weatherObj.tempStatus == "bitter cold"):
            self.rating = "POOR"
            self.weatherEmoji = "⛄❄️"
        elif (self.weatherObj.tempStatus in ["cold", "frigid"]):
            if (self.weatherObj.rain):
                self.rating = "POOR"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "⛄❄️"
            else:
                if (self.weatherObj.unseasonablyWarm and self.weatherObj.weatherStatus != "frigid"):
                    self.rating = "OPTIMAL"
                    self.rating2 = "; Enjoy the warmth"
                    self.weatherEmoji = "🚴🌡️"
                else:
                    self.rating = "MODERATE"
                    self.rating2 = "; Be prepared for cold"
                    self.weatherEmoji = "⛄❄️"
        elif (self.weatherObj.tempStatus == "brisk"): 
            if (self.weatherObj.rain):
                self.rating = "POOR"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌧️☔"
            else:
                if (self.weatherObj.windy or self.weatherObj.weatherStatus == "windy"):
                    self.rating = "MODERATE"
                    self.rating2 = "; It's windy"
                    self.weatherEmoji = "🌬️"
                else:
                    self.rating = "OPTIMAL"
                    self.rating2 = ", you should"
                    self.weatherEmoji = "🚴👍"
        elif (self.weatherObj.tempStatus in ["mild"]):
            if (self.weatherObj.rain):
                self.rating = "MODERATE"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌧️☔"
            elif (self.weatherObj.windy or self.weatherObj.weatherStatus == "windy"):
                self.rating = "MODERATE"
                self.rating2 = "; It's windy"
            else:
                self.rating = "OPTIMAL"
                self.weatherEmoji = "🚴👍"
        elif (self.weatherObj.tempStatus in ["pleasant temps","warm"]):
            if (self.weatherObj.rain):
                self.rating = "MODERATE"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌧️☔"
            else:
                self.rating = "OPTIMAL"
                self.weatherEmoji = "🚴👍"
        elif (self.weatherObj.tempStatus == "hot"):
            if (self.weatherObj.rain):
                self.rating = "MODERATE"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌡️☔"
            else:
                self.rating = "OPTIMAL"
                self.rating2 = ", but it's hot"
                self.weatherEmoji = "🌡️☀️"
        else:
            self.rating = "NOT SURE(?)"
            self.weatherEmoji = "❔"
        if (self.weatherObj.unseasonablyWarm):
            self.weatherObj.tempStatus = "unseasonably warm"
        ratingList = [self.rating, self.rating2, self.weatherEmoji]
        return ratingList
    def recommendAttire(self):
        #assign self.attire string
        """
        this and makeRecommendation() are evaluating some of the same things, but having
        two separate functions is much cleaner and more readable
        """
        if (self.weatherObj.rain or self.weatherObj.snow):
            #attire must be waterproof
            if (self.weatherObj.tempStatus in ["bitter cold", "frigid", "cold"]):
                self.attire = "Waterproof winter jacket/gloves"
            elif (self.weatherObj.tempStatus == "brisk"):
                self.attire = "Waterproof medium jacket"
            else: 
                self.attire = "Waterproof light jacket"
        else:
            #if dry
            if (self.weatherObj.tempStatus in ["bitter cold", "frigid", "cold"]):
                self.attire = "Winter jacket/gloves"
            elif (self.weatherObj.tempStatus == "brisk"):
                self.attire = "Medium jacket"
            elif (self.weatherObj.tempStatus == "mild"):
                self.attire = "Light jacket"
            else:
                self.attire = "Whatever you want"
        return self.attire
