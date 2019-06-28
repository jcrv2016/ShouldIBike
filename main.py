import csv, datetime, json, math, os, pyowm, pytz, requests, schedule, subprocess, sys, time, tweepy 
#Original Modules, please make sure they're in right dir and importable
import pyowm_weathercodes as wc
import Subway, RoadConditions, SunTimes
from Images import Image, Images
#This contains the API keys
from credentials import *
from datetime import datetime, timedelta

#This program currently is run via an external task scheduler every day, and terminates after the second tweet.

#Global, easy to find VIP variables
LOGPATH = "C:\\shouldibike\\templog.csv"
GPSLOCATION = [40.79, -73.96]
#[numeric end month of possible winter conditions, numeric start of possible winter conditions]. Define both as 0 if winter conditions are nonexistent in locale.
WINTERMONTHS = [4,10] 
AMTWEETTIME = "07:30"
PMTWEETTIME = "17:00"
PUBLISH = True
AIRPORT = "LGA"
EXITTIME = 23
SEASONABLE_CSV_PATH = 'C:\\shouldibike\\nycavgweather.csv'
#IMAGES_TO_PULL = [Image("https://511ny.org/map/Cctv/4616495--17", "BkBr", "Brooklyn Bridge Path"),Image("https://511ny.org/map/Cctv/4616600--17#1550452163802.jpg", "MhnBr2", "Manhattan Bridge Path"), Image("http://207.251.86.238/cctv969.jpg?rand=0.4881279622135668", "wbbBr", "Williamsburg Bridge Path (right side of img)")]
IMAGES_TO_PULL = [Image("http://207.251.86.238/324", "MhnBrEntr", "Manhattan Bridge Entrance"),Image("http://207.251.86.238/cctv14.jpg", "BKBr3", "Brooklyn Bridge Path"), Image("http://207.251.86.238/cctv969.jpg?rand=0.4881279622135668", "wbbBr", "Williamsburg Bridge Path (right side of img)")]
#207.251.86.238/cctv324.jpg
"""
model - call TimeKeeper*Singleton* to count time
            TweetJob (create payload and schedule)  ->  
                TimeKeeper.Schedule() 
                Forecaster() -> 
                Weather ->
                    Weather.update()
                    Recommendation (new)
            TweetPublisher*Singleton* to publish
            ExternalConnection*Singleton* - pingTest and APIConnect    

"""
class Weather(object):
    def __init__(self, location, airport, day=-1):
        #mandatory parameters
        self.location = location
        self.airport = airport
        #misc
        self.attire = ""
        #rain-related attributes
        self.littleRain = False
        self.someRain = False
        self.rainText = ""
        self.rain = False
        #snow-related attributes
        self.littleSnow = False
        self.snowTweet = ""
        self.someSnow = False
        self.winterRoadConditions = ""
        self.wet = False #this belongs here? check
        self.snowy = False
        self.snow = False
        #if current month is within previously defined WINTERMONTHS range, set flag for potential winter conditions
        #i feel like there is a less verbose way to do this
        if (WINTERMONTHS[1] > datetime.now().month > WINTERMONTHS[0]):
            self.winter = False
        else:
            self.winter = True
        #wind-related attributes
        self.windy = False
        self.windString = ""
        self.weatherReading = ""
        self.weatherStatus = "undeclared"
        self.forecastTime = datetime.utcnow()
        self.today = True
        print(str(self.forecastTime))
        if(day!=-1):
            #'day == -1' Tweet is for today. Otherwise, increment days
            #Should just be 0
            incrementedDays = int(day) #is it necessary to cast as an int?
            self.today = False
            self.forecastTime = datetime.now() + timedelta(days=incrementedDays)
            self.forecastTime = datetime(self.forecastTime.year, self.forecastTime.month, self.forecastTime.day, 
                                       6, 0, 0, 0,tzinfo=pytz.timezone('US/Eastern'))
        else:
            
            self.forecasttime = datetime(self.forecastTime.year, self.forecastTime.month, self.forecastTime.day, self.forecastTime.hour, 0,0,0, tzinfo=pytz.timezone('US/Eastern'))
            self.forecastTime += timedelta(hours=6)
            #error will be thrown without 6 hour incrementation - it was tested, and this was the minimum 
            #incrementation that could be used, without an error. ¯\_(ツ)_/¯
            #actually, i am testing with 3 hours. update: failed
        self.dayofWeek = self.dayOfWeek()
        #temperatures
        self.mornTemp = 0
        self.eveTemp = 0
        self.hiTemp = 0
        self.loTemp = 0
        #sunriseTimes
        self.sunriseTime = ""
        self.sunsetTime = ""
        #seasonability
        self.historicAvgTemp = 0
        self.avgDifference = 0
        self.avgTemp = 0
        self.avgCommuteTemp = 0
        self.seasonable = False
        self.unseasonablyWarm = False
        self.unseasonablyCold = False
        self.weatherlist = []
        self.elapsedDays = 0
        self.update()
 
    def update(self): 
        #main weather pull function
        tryCount = 0
        successful = False
        print("Pulling weather for " + str(self.forecastTime))
        print("Current time is " + str(datetime.utcnow()))
        while not successful and tryCount < 20:
            try:
                self.owm = ExternalConnection.getInstance().returnOWMConnection()
                self.Forecaster = self.owm.daily_forecast_at_coords(self.location[0], self.location[1])
                self.weatherReading = self.Forecaster.get_weather_at(self.forecastTime)
                successful = True
            except:
                tryCount += 1
                print("Try failed on attempt " + str(tryCount) + ".")
        if tryCount >= 20:
            print("\nCannot connect to pyOWM API. Exiting")
            exit()
        self.getWind()
        self.getTemp()
        self.getRain()
        self.getSnow()
        self.getSunTimes()
        if (self.winter and self.today):
            roads = RoadConditions.RoadConditions()
            self.winterRoadConditions = roads.text
            self.snowy, self.wet = roads.snowy, roads.wet
        self.interpretWeatherCode()
        self.isSeasonable()
        self.interpretTemp()
       
        
    def mmToIn(self, mm):
        mm *= 0.0393701
        return mm

    def getSunTimes(self):
        suntimes = SunTimes.SunTimes(self)
        self.sunriseTime, self.sunsetTime = suntimes.getSunTimes()

    def getSnow(self):
        if (self.winter):
            if (self.weatherReading.get_snow()): 
                snow = self.weatherReading.get_snow() 
                if 'all' in snow:
                    snowStatus = snow['all']
                    if (snowStatus >= 2.5):
                        snowStatus = self.mmToIn(snowStatus)
                        snowStatus = "{:.1f}".format(snowStatus) 
                        self.snowTweet = snowStatus + '" snow'
                        self.someSnow = True
                    else:
                        self.littleSnow = True
            else: 
                self.littleSnow = True
                self.snowTweet = "no snow"

    def getWind(self):
        if (self.weatherReading.get_wind()):
            wind = self.weatherReading.get_wind()
            if ('speed' in wind):
                windSpeed = (wind['speed']) * 2.23694 #convert m/s to mph
                if (windSpeed >= 15):
                    self.windy = True
                self.windString = str(math.ceil(windSpeed)) + " mph wind"
            else: self.windString = " no wind"
          
    def getTemp(self):
        temperature = self.weatherReading.get_temperature('fahrenheit') 
        self.mornTemp = temperature['morn']
        self.eveTemp = temperature['eve']
        self.hiTemp = temperature['max']
        self.loTemp = temperature['min']
        self.avgTemp = ((self.hiTemp + self.loTemp)/2)
        self.avgCommuteTemp = ((self.mornTemp + self.eveTemp)/2)
        
    def getRain(self):
        if (self.weatherReading.get_rain()): 
            rain = self.weatherReading.get_rain() 
            if ('all' in rain):
                rainStatus = rain['all']
                rainCutoff = 7.62
                if (rainStatus > rainCutoff):
                    self.rainText = format(self.mmToIn(rainStatus), '.1f') + '" rain'
                    self.someRain = True
                    self.rain = True         
                else:
                    self.littleRain = True
                    self.rain = False
        else: 
            self.littleRain = True
            self.rainText = "no rain"
            self.rain = False
      
    def interpretWeatherCode(self):
        #pull weather code and make human-readable
        #listing of weather codes is here: https://openweathermap.org/weather-conditions
        #future changes:
        #sunny would be more descriptive than clear in applicable cases
        #make it so "frigid" or "very hot" in weatherStatus can't be posted alongside "frigid" or "very hot" in tempStatus
        
        self.weatherCode = self.weatherReading.get_weather_code()

        for i in range(len(wc.weathers)):
            for x in range(len(wc.weathers[i])):
                if (self.weatherCode == wc.weathers[i][x]):
                    self.weatherStatus = wc.weathers[i][0]
                    break
                else:
                    continue                  

        if (self.weatherStatus in ["rain", "light rain", "hail"]):
           if (self.littleRain):
                self.weatherStatus = "trace rain"
                self.rain = False
           else:
                self.rain = True
       
        if (self.weatherStatus == "snow"):
           if (self.littleSnow):
                self.weatherStatus = "flurries"
           else:
                self.snow = True
   
    def interpretTemp(self):
        if (self.avgCommuteTemp < 18):
            self.tempStatus = "bitter cold"
        elif (18 <= self.avgCommuteTemp < 26):
            self.tempStatus = "frigid"
        elif (26 <= self.avgCommuteTemp < 41):
            self.tempStatus = "cold"
        elif (41 <= self.avgCommuteTemp < 52):
            self.tempStatus = "brisk"
        elif (52 <= self.avgCommuteTemp < 65):
            self.tempStatus = "mild"
        elif (65 <= self.avgCommuteTemp < 74):
            self.tempStatus = "pleasant temps"
        elif (74 <= self.avgCommuteTemp < 84):
            self.tempStatus = "warm"
        elif (self.avgCommuteTemp >= 84):
            self.tempStatus = "hot"
        else:
            self.tempStatus = "undeclared"

    def getElapsedDays(self):
        forecastTime = self.forecastTime.replace(tzinfo=None)
        start = datetime(self.forecastTime.year, 1,1)
        elapsedDate = forecastTime - start
        self.elapsedDays =  elapsedDate.days
        #if leap year, use 365th day of year instead of 366th
        if self.elapsedDays >= 365:
            self.elapsedDays == 364

    def dayOfWeek(self):
        dayMapLong = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dayMapShort = ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]
        self.dayofWeek = {}
        self.dayofWeek["short"] = dayMapShort[self.forecastTime.weekday()]
        self.dayofWeek["long"] = dayMapLong[self.forecastTime.weekday()]
        return self.dayofWeek


    def isSeasonable(self):
        fileOpened = True
        seasonable = [-5, 5] #Set range of what a seasonable temp variance is. This is just my opinion
        self.getElapsedDays()
        if not (self.weatherlist): 
            #external file reader func here? where located tho?
            try:
                with open(SEASONABLE_CSV_PATH, 'r') as csvfile:
                    reader=csv.reader(csvfile)
                    for row in reader:
                        self.weatherlist.append(row)
                csvfile.close()
            except:
                fileOpened = False
                
        if (fileOpened):
            self.historicAvgTemp = float(self.weatherlist[self.elapsedDays][1])
            self.avgDifference = self.avgTemp - self.historicAvgTemp

            if (seasonable[0] < self.avgDifference < seasonable[1]):
                self.seasonable = True
            else:
                self.seasonable = False
                if (self.avgDifference >= seasonable[1]):
                    self.unseasonablyWarm = True
                else:                       
                    self.unseasonablyCold = True 
        else:
            self.seasonable = True
            self.unseasonablyWarm = False
            self.unseasonablyCold = False

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
            self.rating2 = "; Only for diehards"
            self.weatherEmoji = "⛄❄️"
        elif (self.weatherObj.tempStatus in ["cold", "frigid"]):
            if (self.weatherObj.rain):
                self.rating = "POOR"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "⛄❄️"
            else:
                if (self.weatherObj.unseasonablyWarm and self.weatherObj.weatherStatus != "frigid"):
                    self.rating = "PROBABLY"
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
        elif (self.weatherObj.tempStatus == "very warm"):
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

class TweetPublisher(object): 
    def __init__(self, tweetContents, images=None):
        self.tweetContents = tweetContents
        if (images):
            self.images = images
        else:
            self.images = None
            #necessary?
        self.tweetError = False
        self.publishTweet()
    def publishTweet(self):
        print(self.tweetContents)
        if(PUBLISH):
            try:
                twitter = ExternalConnection.getInstance().returnTwitterConnection()
                if (self.images):
                    media_ids = []
                    for filename in self.images:
                        res = twitter.media_upload(filename)
                        media_ids.append(res.media_id)
                    twitter.update_status(status=self.tweetContents, media_ids=media_ids)
                else:
                    twitter.update_status(self.tweetContents)
                    print("\nTweet successfully published")
            except:
                print("\nTweet not successfully published")
                self.tweetError = True

    def log(self):
        self.publishAttemptTime = datetime.now(pytz.timezone('US/Eastern'))
        contents = [("WANup =" + str(self.WANup)), ("tweetAttemptTime =" + str(self.publishAttemptTime))]
        if(self.WANup == True):
            contents += [("wind= " + self.weatherObj.windString), ("rain= " + str(self.weatherObj.rainText)), 
                   ("rating= " + self.weatherObj.rating), ("rating2= " + self.weatherObj.rating2), ("forecastTime= " + str(self.weatherObj.forecastTime)), 
                   ("today= " + str(self.weatherObj.today)), ("mornTemp= " + str(self.weatherObj.mornTemp)), 
                   ("eveTemp =" + str(self.weatherObj.eveTemp)), ("tempStatus= " + str(self.weatherObj.tempStatus)), ("weatherStatus= " + str(self.weatherObj.weatherStatus)), 
                   ("attire =" + self.weatherObj.attire), ("tweetLength =" + str(self.tweetLength)), ("tweetError =" + str(self.tweetError))]
        outputFile = open(LOGPATH, 'a')
        outputWriter = csv.writer(outputFile)
        outputWriter.writerow(contents)
        outputFile.close()

class TweetJob(object):
    def __init__(self, argument, tweetTime):
        self.argument, self.tweetTime = argument, tweetTime
        self.truncationAttempted = False
        self.punctuation = ""    
        self.tweetContents = ""
        self.weekend = False
        self.tk = TimeKeeper.getInstance()
        self.processJobs()
        #declare suntimes variables 
    def processJobs(self):
        
        if (self.argument == "AMTweet"):
            self.tk.schedule(self.AMTweet, self.tweetTime) 
        elif (self.argument == "PMTweet"):
            self.tk.schedule(self.PMTweet, self.tweetTime)
        elif (self.argument == "WeekendTweet"):
            self.tk.schedule(self.WeekendTweet, self.tweetTime)
        elif (self.argument == "WeekTweet"):
            self.tk.schedule(self.WeekTweet, self.tweetTime)
        elif (self.argument == "ImageTweet"):
            self.tk.schedule(self.ImageTweet, self.tweetTime)
        elif (self.argument == "TestTweet"):
            self.tk.schedule(self.TestTweet, self.tweetTime)
        print("Successfully scheduled " + self.argument)
    def AMTweet(self):
        self.weatherObj = Weather(GPSLOCATION, AIRPORT)
        self.rec = Recommendation(self.weatherObj)
        self.formTweet()
        TweetPublisher(self.tweetContents)
    def PMTweet(self):
        self.weatherObj = Weather(GPSLOCATION, AIRPORT, 1)
        self.rec = Recommendation(self.weatherObj)
        self.formTweet()
        TweetPublisher(self.tweetContents)
    def WeekTweet(self):
        self.weatherList = []
        tempTweet = ""
        for x in range (1,6):
            self.weatherObj = Weather(GPSLOCATION, AIRPORT, x)
            self.rec = Recommendation(self.weatherObj)
            self.weatherList.append(self.weatherObj)
            tempTweet += self.weatherObj.dayofWeek["short"] + "- " + str(self.rec.rating) + "/" 
            tempTweet += self.weatherObj.weatherStatus + "/Morn " + str(math.ceil(self.weatherObj.mornTemp)) + "°F/Eve " + str(math.ceil(self.weatherObj.eveTemp)) + "°F\n"
        self.tweetContents = "THIS WEEK'S CONDITIONS:\n" + tempTweet
        TweetPublisher(self.tweetContents)
    def WeekendTweet(self):
        self.weatherList = []
        self.tempTweet = "THIS WEEKEND: "
        for x in range (1,3):
            #Not ready
            #Way too long. Get rid of redundant text - "Forecast, looks like", suntimes, emojis, rating2
            #print text error if too long
            self.Weekend = True
            self.weatherObj = Weather(GPSLOCATION, AIRPORT, x)
            self.rec = Recommendation(self.weatherObj)
            self.formTweet()
            self.tempTweet += "Internal Count " + str(x) + "\n" + self.tweetContents
        self.tweetContents = self.tempTweet
        TweetPublisher(self.tweetContents)
    def ImageTweet(self):
        # This was turned off. It should be triggered in the PM if the weather is currently shit, or if it WAS shit during the AM
        images = Images(IMAGES_TO_PULL)
        self.paths = []
        self.tweetContents= "Current views of "
        
        for items in IMAGES_TO_PULL[:-1]:
            self.tweetContents += items.description + ", "
            self.paths.append(items.localPath)
        self.tweetContents += images.downloadJobs[-1].description + ". Via DOT traffic camera feeds."
        self.paths.append(images.downloadJobs[-1].localPath)
        self.images = self.paths
        TweetPublisher(self.tweetContents, self.images)

    def recommendation(self):
        self.rec = Recommendation(self.weatherObj)
        #import variables here
        #type that shit out
    def printTweet(self):
        print(self.tweetContents)

    #imported from old class, to merge in
    def todayStatus(self):
        self.tweetContents = self.rec.rating  
        if (self.rec.rating2):
            self.tweetContents += self.rec.rating2 + self.punctuation
        else:
            self.tweetContents += self.punctuation
        self.tweetContents += " Today's " 
    
    def tomorrowStatus(self):
        self.tweetContents += self.weatherObj.dayofWeek["long"].upper() + ": Looks like " + self.rec.rating      
        if (self.rec.rating2):
            self.tweetContents += self.rec.rating2
        self.tweetContents += self.punctuation + " Forecast: "

    def formTweet(self):
        if (self.rec.rating == "OPTIMAL"): #=="YES:
            self.punctuation = "."
        else:
            self.punctuation = "."
        if (self.weatherObj.today):
            #tweet current day's conditions
            self.todayStatus()  
        else:
            #tweet for future date
            self.tomorrowStatus()
        self.tweetContents += self.weatherObj.tempStatus 
        
        #if rain or snow doesn't exist, print weather status
        if (not self.weatherObj.rain and not self.weatherObj.snow):
            self.tweetContents += "/" + self.weatherObj.weatherStatus
        #if rainText or snowtweet exist (ie some rain, no rain, NOT trace rain OR some snow, NOT flurries) exists, print rainText and/or snowtweet (if winter)
        if ((self.weatherObj.rainText) and (self.weatherObj.weatherStatus != "trace rain")):
            self.tweetContents += "/" + self.weatherObj.rainText
        if ((self.weatherObj.snowTweet) and self.weatherObj.weatherStatus != "flurries" and self.weatherObj.winter):
            self.tweetContents += "/" + self.weatherObj.snowTweet
        self.tweetContents += "/" + self.weatherObj.windString + ". " + "Morning " + str(math.ceil(self.weatherObj.mornTemp)) + "°F/Evening " 
        self.tweetContents += str(math.ceil(self.weatherObj.eveTemp)) + "°F/" 
        if (self.weatherObj.sunriseTime and self.weatherObj.sunsetTime):
            self.tweetContents += "Sunrise " + str(self.weatherObj.sunriseTime) + "/Sunset " + str(self.weatherObj.sunsetTime) + " "
 
        # Append weatherEmoji
        if(self.rec.weatherEmoji):
            self.tweetContents += self.rec.weatherEmoji
        if(self.weatherObj.today):
            if (self.weatherObj.winterRoadConditions):
                self.tweetContents += self.weatherObj.winterRoadConditions
            if (self.rec.attire):
                self.tweetContents += "\nWear: " + self.rec.attire
            subway = Subway.Subway()
            if(subway.apiUp):
                self.tweetContents += subway.printStatus() + " "
        self.tweetLength = len(self.tweetContents)
        
        if (self.tweetLength <= 261):
            self.tweetContents += "\n#bikenyc"
            self.tweetLength = len(self.tweetContents)
        
        if (self.tweetLength > 270 and not self.truncationAttempted):
            self.truncate()
            self.truncationAttempted = True
            self.formTweet()

    def truncate(self):
        self.tweetContents = ""
        self.weatherObj.weatherEmoji = ""
        if(self.tweetLength > 276):
            self.rec.rating2 = ""

class ExternalConnection(object):
    __instance = None
    @staticmethod
    def getInstance():
        if ExternalConnection.__instance == None:
            ExternalConnection()
        return ExternalConnection.__instance
    def __init__(self):
        if ExternalConnection.__instance !=None:
            raise Exception ("This class is a singleton")
        else:
            ExternalConnection.__instance = self
            self.api = ""
            self.TweetAPIConnect()
            self.pyOWMConnect()
    def TweetAPIConnect(self):
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
        self.api = tweepy.API(auth)
        print("\nSuccessfully connected to Twitter API.\n")
        #needs a disconnect
    def pyOWMConnect(self):
        #initialize OWM object with API key
        self.owm = pyowm.OWM(OWM_KEY)
        print("\nSuccessfully connected to PYOWM API.")
    def pingTest(self):
        #this will ping infinitely on linux without the -c parameter
        hostname = "twitter.com"
        with open(os.devnull, 'w') as DEVNULL:
            try:
                subprocess.check_call(
                    ['ping', hostname],
                    stdout=DEVNULL,  # suppress output
                    stderr=DEVNULL
                )
                isUp = True
            except subprocess.CalledProcessError:
                isUp = False
        return isUp
    def WANtest(self):
        #run pingTest up to maxTries. return result of pingTest
        WANup = False
        tryCount = 1
        maxTries = 10
        waitTime = 5
        while(WANup == False and tryCount <= maxTries):
            if(self.pingTest()):
                #test connectivity
                WANup = True
                if(tryCount > 1):
                    print("\nWAN was down, but was restored.")
                return WANup
            else:
                print("\nWAN down. Try " + str(tryCount) + " failed. Waiting " + str(waitTime) + " seconds to retry.")
                time.sleep(waitTime)
                tryCount +=1
                if(tryCount > maxTries):
                    print("\nMax tries attempted.")
                    return WANup
    def returnTwitterConnection(self):
        return self.api
    def returnOWMConnection(self):
        return self.owm
class TimeKeeper(object):
    #singleton wrapper
    __instance = None
    @staticmethod
    def getInstance():
        """ Static access method """
        if TimeKeeper.__instance == None:
            TimeKeeper()
        return TimeKeeper.__instance
    def __init__(self):
        if TimeKeeper.__instance != None:
            raise Exception ("This class is a singleton")
        else:
            TimeKeeper.__instance = self
            self.dateandtime = ""
            self.updateTime()
            self.dayOfWeek()
            
    def updateTime(self):
        self.dateandtime = datetime.now(pytz.timezone('US/Eastern'))

    def dayOfWeek(self):
        dayMapLong = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dayMapShort = ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]
        self.dayofWeek = {}
        self.dayofWeek["short"] = dayMapShort[self.dateandtime.weekday()]
        self.dayofWeek["long"] = dayMapLong[self.dateandtime.weekday()]
        return self.dayofWeek

    def schedule(self, job, time1):
        schedule.every().day.at(time1).do(job)
        print("\nWaiting for scheduled time (" + str(time1) + ")...\n") #print name of job 
    def runJobs(self):
        print("Scheduler started at " + str(self.dateandtime) + ".")
        while (self.dateandtime.hour < EXITTIME):
            schedule.run_pending()
            time.sleep(20) # wait 20 sec
            self.updateTime()
        print("Exit hour of " + str(EXITTIME) + " reached at " + str(self.dateandtime) + ", program exiting.")
        sys.exit()
        
#MAIN GOES HERE
#weekend should not use commute times for formulation. should include peak of day
timekeeper = TimeKeeper()
externalconnection = ExternalConnection()

TweetJob("AMTweet", AMTWEETTIME)
if (timekeeper.dayofWeek["long"] in ["Friday"]):
    TweetJob("WeekendTweet", PMTWEETTIME)
elif (timekeeper.dayofWeek["long"] in ["Sunday"]):
    TweetJob("WeekTweet", PMTWEETTIME)
else:
    TweetJob("PMTweet", PMTWEETTIME)
TweetJob("ImageTweet", AMTWEETTIME)
timekeeper.runJobs()




    

 


























































