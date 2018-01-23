import csv, datetime, json, math, os, pyowm, pytz, schedule, subprocess, sys, time, tweepy, urllib.request
import xml.etree.ElementTree as ET
from credentials import *
from datetime import datetime, timedelta

class Weather(object):
    def __init__(self, location, airport, tweetTime, day=-1):
        #parameters
        self.location = location
        self.airport = airport
        #misc
        self.attire = ""
        #rain-related attributes
        self.littleRain = False
        self.someRain = False
        self.rainTweet = ""
        self.minorRain = False
        self.rain = False
        #snow-related attributes
        self.littleSnow = False
        self.snowTweet = ""
        self.someSnow = False
        self.minorRain = False
        self.winterRoadConditions = ""
        self.wet = False
        self.snowy = False
        self.snow = False
        #if it's November to April, set flag for potential winter conditions 
        if (10 > datetime.now().month > 5):
            self.winter = False
        else:
            self.winter = True
        #wind-related attributes
        self.windy = False
        self.windString = ""
        self.weatherReading = ""
        self.weatherStatus = "undeclared"
        self.rating = ""
        self.rating2 = "" 
        self.forecastTime = datetime.utcnow()
        self.today = True
        if(day!=-1):
            #increment days
            incrementedDays = int(day)
            self.today = False
            self.forecastTime = datetime.now() + timedelta(days=incrementedDays)
            self.forecastTime = datetime(self.forecastTime.year, self.forecastTime.month, self.forecastTime.day, 
                                       6, 0, 0, 0,tzinfo=pytz.timezone('US/Eastern'))
        self.owm = pyowm.OWM(OWM_KEY)
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
        self.unseasonablyWarm = True
        self.unseasonablyCold = True
        self.weatherlist = []
        self.elapsedDays = 0
        #weatherCodes
        self.rainCodes = ["rain", 200, 201, 202, 210, 211, 212, 221, 230, 231, 232, 302, 312, 313, 314, 501, 502, 503, 504, 511, 522, 531, 901, 906, 960]
        self.lightRainCodes = ["light rain", 300, 301, 302, 310, 311, 321, 500, 520, 521, 701]
        self.snowyCodes = ["snowy", 600, 601, 602, 611, 612, 615, 616, 620, 621, 622]
        self.limitedVisibilityCodes = ["limited visiblity", 711, 721, 731, 751, 761, 762]
        self.clearCodes = ["clear", 741, 800, 801, 802, 803, 804, 951, 952, 953]
        self.extremeWeatherCodes = ["extreme weather", 771, 781, 900, 902, 959, 961, 962]
        self.frigidCodes = ["frigid", 903]
        self.veryHotCodes = ["very hot", 904]
        self.windyCodes = ["windy", 905, 954, 955, 956, 957, 958]
        self.hailCodes = ["hail", 906]
        self.weathers = [self.rainCodes, self.lightRainCodes, self.snowyCodes, self.limitedVisibilityCodes, self.clearCodes, 
                         self.extremeWeatherCodes, self.frigidCodes, self.veryHotCodes, self.windyCodes, self.hailCodes]
        #initialize tweet object
        self.messsage = Tweet(self, tweetTime)
 
    def updateWeather(self):
        #main weather pull function
        self.Forecaster = self.owm.daily_forecast_at_coords(self.location[0], self.location[1])
        if (self.today):
            self.forecast = self.Forecaster.get_forecast() #return list of Weather objects
            self.weatherReading = self.forecast.get(0) #get current Weather
        else:
            self.weatherReading = self.Forecaster.get_weather_at(self.forecastTime)
        self.getWind()
        self.getTemp()
        self.getRain()
        self.getSnow()
        if (self.winter and self.today):
            roads = RoadConditions()
            self.winterRoadConditions = roads.text
            self.snowy, self.wet = roads.snowy, roads.wet
        self.interpretWeatherCode()
        self.isSeasonable()
        self.interpretTemp()
        self.makeRecommendation()
        self.recommendAttire()
        suntimes = SunTimes(self)
        self.sunriseTime, self.sunsetTime = suntimes.getSunTimes()

    def mmtoIn(self, mm):
        mm *= 0.0393701
        return mm

    def getSnow(self):
        if (self.winter):
            if (self.weatherReading.get_snow()): 
                snow = self.weatherReading.get_snow() 
                if 'all' in snow:
                    snowStatus = snow['all']
                    if (snowStatus >= 2.5):
                        if (snowStatus < 3.8):
                            self.minorSnow = True
                        snowStatus = self.mmtoIn(snowStatus)
                        snowStatus = "{:.1f}".format(snowStatus) 
                        self.snowTweet = snowStatus + '" snow'
                        self.someSnow = True
                    elif (0 < snowStatus < 2.5):
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
                if (rainStatus >= 2.5):
                    if (rainStatus < 3.8):
                        self.minorRain = True
                    rainStatus = self.mmtoIn(rainStatus)
                    rainStatus = format(rainStatus, '.1f')
                    self.rainTweet = rainStatus + '" rain'
                    self.someRain = True
                elif (rainStatus > 0 < 2.5):
                    self.littleRain = True
        else: 
            self.littleRain = True
            self.rainTweet = "no rain"
      
    def interpretWeatherCode(self):
        #pull weather code and make human-readable
        #listing of weather codes is here:https:  //openweathermap.org/weather-conditions
        #future changes:
        #sunny would be more descriptive than clear in applicable cases
        #make it so "frigid" or "very hot" in weatherStatus can't be posted alongside "frigid" or "very hot" in tempStatus
        
        self.weatherCode = self.weatherReading.get_weather_code()

        for i in range(len(self.weathers)):
            for x in range(len(self.weathers[i])):
                if (self.weatherCode == self.weathers[i][x]):
                    self.weatherStatus = self.weathers[i][0]
                    break
                else:
                    continue                  

        if (self.weatherStatus in ["rain", "light rain", "hail"]):
           if (self.littleRain):
                self.weatherStatus = "trace rain"
           else:
                self.rain = True
       
        if (self.weatherStatus == "snowy"):
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
        elif (52 <= self.avgCommuteTemp < 64):
            self.tempStatus = "mild"
        elif (64 <= self.avgCommuteTemp < 74):
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

    def isSeasonable(self):
        path = 'C:\\shouldibike\\nycavgweather.csv'
        fileOpened = True
        self.getElapsedDays()
        if not (self.weatherlist): 
            try:
                with open(path, 'r') as csvfile:
                    reader=csv.reader(csvfile)
                    for row in reader:
                        self.weatherlist.append(row)
                csvfile.close()
            except:
                fileOpened = False
                
        if (fileOpened):
            self.historicAvgTemp = float(self.weatherlist[self.elapsedDays][1])
            self.avgDifference = self.avgTemp - self.historicAvgTemp

            if (-5 >= self.avgDifference <= 5):
                self.seasonable = True
                self.unseasonablyWarm = False
                self.unseasonablyCold = False
            else:
                self.seasonable = False
                if (self.avgDifference >= 5):
                    self.unseasonablyWarm = True
                else:                       
                    self.unseasonablyCold = True 
        else:
            self.seasonable = True
            self.unseasonablyWarm = False
            self.unseasonablyCold = False

    def recommendAttire(self):
        #assign self.attire string
        """
        this and makeRecommendation() are evaluating some of the same things, but having
        two separate functions is much cleaner and more readable
        """
        if (self.rain or self.snow):
            #attire must be waterproof
            if (self.tempStatus in ["bitter cold", "frigid", "cold"]):
                self.attire = "Waterproof winter jacket/gloves"
            elif (self.tempStatus == "brisk"):
                self.attire = "Waterproof medium jacket"
            else: 
                self.attire = "Waterproof light jacket"
        else:
            #if dry
            if (self.tempStatus in ["bitter cold", "frigid", "cold"]):
                self.attire = "Winter jacket/gloves"
            elif (self.tempStatus == "brisk"):
                self.attire = "Medium jacket"
            elif (self.tempStatus == "mild"):
                self.attire = "Light jacket"
            else:
                self.attire = "Summer attire"
    def makeRecommendation(self):
        if (self.snow):
            self.rating = "PROBABLY NOT"
            self.rating2 = "; Be prepared for snow"
            self.weatherEmoji = "⛄❄️"
        elif (self.snowy):
            self.rating = "PROBABLY NOT"
            self.rating2 = "; Roads are likely messy"
            self.weatherEmoji = "⛄❄️"
        elif (self.weatherStatus in ["extreme weather"]):
            self.rating = "NO"
            self.weatherEmoji = "⚡❕"
        elif (self.tempStatus == "bitter cold"):
            self.rating = "PROBABLY NOT"
            self.rating2 = "; Only for diehards"
            self.weatherEmoji = "⛄❄️"
        elif (self.tempStatus in ["cold", "frigid"]):
            if (self.rain):
                self.rating = "PROBABLY NOT"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "⛄❄️"
            else:
                if (self.unseasonablyWarm and self.weatherStatus != "frigid"):
                    self.rating = "PROBABLY"
                    self.rating2 = "; Enjoy the warmth"
                    self.weatherEmoji = "🚴🌡️"
                else:
                    self.rating = "MAYBE"
                    self.weatherEmoji = "⛄❄️"
        elif (self.tempStatus == "brisk"): 
            if (self.rain):
                self.rating = "PROBABLY NOT"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌧️☔"
            else:
                if (self.windy or self.weatherStatus == "windy"):
                    self.rating = "MAYBE"
                    self.rating2 = "; It's windy"
                    self.weatherEmoji = "🌬️"
                else:
                    self.rating = "YES"
                    self.rating2 = ", you should"
                    self.weatherEmoji = "🚴👍"
        elif (self.tempStatus in ["mild"]):
            if (self.rain):
                self.rating = "MAYBE"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌧️☔"
            elif (self.windy or self.weatherStatus == "windy"):
                self.rating = "MAYBE"
                self.rating2 = "; It's windy"
            else:
                self.rating = "YES"
                self.rating2 = ", you should"
                self.weatherEmoji = "🚴👍"
        elif (self.tempStatus in ["pleasant temps","warm"]):
            if (self.rain):
                self.rating = "MAYBE"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌧️☔"
            else:
                self.rating = "YES"
                self.rating2 = ", you should"
                self.weatherEmoji = "🚴👍"
        elif (self.tempStatus == "very warm"):
            if (self.rain):
                self.rating = "MAYBE"
                self.rating2 = "; Be prepared for rain"
                self.weatherEmoji = "🌡️☔"
            else:
                self.rating = "YES"
                self.rating2 = ", but it's hot"
                self.weatherEmoji = "🌡️☀️"
        else:
            self.rating = "NOT SURE(?)"
            self.weatherEmoji = "❔"
class SunTimes(object):
    def __init__(self, Weather):
        self.WeatherObj = Weather
        self.airport = self.WeatherObj.airport
        self.today = self.WeatherObj.today
        self.forecastTime = self.WeatherObj.forecastTime
        self.sunriseTime = ""
        self.sunsetTime = ""

    def parseJSON(self, url, string):
        response = urllib.request.urlopen(url)
        JSONdata = json.loads(response.read())
        if (string in JSONdata):   
           return (JSONdata[string])
        else:
           return None

    def formatTime(self, time):
        formattedTime = datetime.strptime(time,"%H:%M:%S %p")
        formattedTime = formattedTime.strftime('%#H:%M')
        return formattedTime
   
    def getSunTimes(self):
        URL = "https://apps.tsa.dhs.gov/MyTSAWebService/GetEventInfo.ashx?&output=json&airportcode=" + self.airport
        sunriseURL = URL + "&eventtype=sunrise"
        sunsetURL = URL + "&eventtype=sunset"
        if (not self.today):
            APIDateString = "&eventdate=" + f"{self.forecastTime:%m/%d/%y}"
            sunriseURL += APIDateString
            sunsetURL += APIDateString
        try:
            self.sunriseTime = self.parseJSON(sunriseURL, "Sunrise")
            self.sunsetTime = self.parseJSON(sunsetURL, "Sunset")
            self.sunriseTime = self.formatTime(self.sunriseTime)
            self.sunsetTime = self.formatTime(self.sunsetTime)
        except:
            #keep self.sunriseTime and self.sunsetTime empty
            pass
        return self.sunriseTime, self.sunsetTime

class Tweet(object):
    def __init__(self, Weather, tweetTime):
        self.logPath = 'C:\\shouldibike\\templog.csv'
        if(self.WANtest()):      
            #test connectivity
            #set attributes
            auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
            auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
            self.api = tweepy.API(auth)
            self.tweetTime = 0
            self.weatherObj = Weather
            #self.followerList = []
            self.tweetError = False
            self.tweetLength = 0
            self.publishAttemptTime = 0
            self.tweetContents = ""
            self.schedulePublish(tweetTime)
        else:
            print("\nCannot initialize object. WAN down. Logging failure.")
            self.log()
            sys.exit()
    def formTweet(self):
        if (self.weatherObj.unseasonablyWarm):
            self.weatherObj.tempStatus = "unseasonably warm"
        if (self.weatherObj.rating == "YES"):
            punctuation = "!"
        else:
            punctuation = "."
        if (self.weatherObj.today):
            #tweet current day's conditions
            self.tweetContents = self.weatherObj.rating
            
            if (self.weatherObj.rating2):
                self.tweetContents += self.weatherObj.rating2 + punctuation
            else:
                self.tweetContents += punctuation
            self.tweetContents += " Today's "      
        else:
            #tweet for Tomorrow
            self.tweetContents += "TOMORROW: Looks like " + self.weatherObj.rating 
            
            if (self.weatherObj.rating2):
                self.tweetContents += self.weatherObj.rating2
            self.tweetContents += punctuation + " Forecast: "
        self.tweetContents += self.weatherObj.tempStatus 
        
        #if rain or snow doesn't exist, print weather status
        if (not self.weatherObj.rain and not self.weatherObj.snow):
            self.tweetContents += "/" + self.weatherObj.weatherStatus
        #if raintweet or snowtweet exist (ie some rain, no rain, NOT trace rain OR some snow, NOT flurries) exists, print raintweet and/or snowtweet (if winter)
        if ((self.weatherObj.rainTweet) and (self.weatherObj.weatherStatus != "trace rain")):
            self.tweetContents += "/" + self.weatherObj.rainTweet
        if ((self.weatherObj.snowTweet) and self.weatherObj.weatherStatus != "flurries" and self.weatherObj.winter):
            self.tweetContents += "/" + self.weatherObj.snowTweet
        self.tweetContents += "/" + self.weatherObj.windString + ". " + "Morning " + str(math.ceil(self.weatherObj.mornTemp)) + "°F/Evening " 
        self.tweetContents += str(math.ceil(self.weatherObj.eveTemp)) + "°F/" 
        if (self.weatherObj.sunriseTime):
            self.tweetContents += "Sunrise " + str(self.weatherObj.sunriseTime) + "/Sunset " + str(self.weatherObj.sunsetTime) + " "
 
        # Append weatherEmoji
        if(self.weatherObj.weatherEmoji):
            self.tweetContents += self.weatherObj.weatherEmoji
        if(self.weatherObj.today):
            if (self.weatherObj.winterRoadConditions):
                self.tweetContents += self.weatherObj.winterRoadConditions
            if (self.weatherObj.attire):
                self.tweetContents += "\nWear: " + self.weatherObj.attire
            subway = Subway()
            if(subway.apiUp):
                self.tweetContents += subway.printStatus() + " "
        self.tweetLength = len(self.tweetContents)
        if (self.tweetLength <= 261):
            self.tweetContents += "\n#bikenyc"
            self.tweetLength = len(self.tweetContents)        

    def truncate(self):
        self.tweetContents = ""
        self.weatherObj.weatherEmoji = ""
        if(self.tweetLength > 276):
            self.weatherObj.rating2 = ""
   
    def printTweet(self):
        print(self.tweetContents)
   
    def followBack(self):
        for follower in tweepy.Cursor(self.api.followers).items():
            try:            
                follower.follow()
            except:
                print("\nCouldn't follow " + follower.screen_name)
            else:
                print("\nFollowed " + follower.screen_name)

    def updateStatus(self):
        try:
            self.api.update_status(self.tweetContents)
            print("\nTweet successfully published")
        except:
            print("\nTweet not successfully published")
            self.tweetError = True
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
        self.WANup = False
        tryCount = 1
        maxTries = 10
        while(self.WANup == False and tryCount <= maxTries):
            if(self.pingTest()):
                #test connectivity
                self.WANup = True
                if(tryCount > 1):
                    print("\nWAN was down, but was restored.")
                return self.WANup
            else:
                waitTime = 5
                print("\nWAN down. Try " + str(tryCount) + " failed. Waiting " + str(waitTime) + " seconds to retry.")
                time.sleep(waitTime)
                tryCount +=1
                if(tryCount > maxTries):
                    print("\nMax tries attempted.")
                    return self.WANup
    def publish(self):
        self.weatherObj.updateWeather()
        self.formTweet()
        if (self.tweetLength > 270):
            self.truncate()
            self.formTweet()
        self.updateStatus()     
        self.printTweet()
        self.followBack()
        self.log()     
    def schedulePublish(self, time1):
        schedule.every().day.at(time1).do(self.publish)
        print("\nWaiting for scheduled time (" + str(time1) + ")...\n")     
    def log(self):
        self.publishAttemptTime = datetime.now(pytz.timezone('US/Eastern'))
        contents = [("WANup =" + str(self.WANup)), ("tweetAttemptTime =" + str(self.publishAttemptTime))]
        if(self.WANup == True):
            contents += [("wind= " + self.weatherObj.windString), ("rain= " + str(self.weatherObj.rainTweet)), 
                   ("rating= " + self.weatherObj.rating), ("rating2= " + self.weatherObj.rating2), ("forecastTime= " + str(self.weatherObj.forecastTime)), 
                   ("today= " + str(self.weatherObj.today)), ("mornTemp= " + str(self.weatherObj.mornTemp)), 
                   ("eveTemp =" + str(self.weatherObj.eveTemp)), ("tempStatus= " + str(self.weatherObj.tempStatus)), ("weatherStatus= " + str(self.weatherObj.weatherStatus)), 
                   ("attire =" + self.weatherObj.attire), ("tweetLength =" + str(self.tweetLength)), ("tweetError =" + str(self.tweetError))]
        outputFile = open(self.logPath, 'a')
        outputWriter = csv.writer(outputFile)
        outputWriter.writerow(contents)
        outputFile.close()

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
            if(keyword):
                self.text += string + "- "
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
        return self.text
class RoadConditions(object):
    def __init__(self):
        self.url = "https://511ny.org/api/getwinterroadconditions?key=" + NY511_KEY + "&format=xml"
        self.wet = False
        self.snowy = False
        self.text = ""
        self.pullData()
    def pullData(self):
        try:
            response = urllib.request.urlopen(self.url)
            tree = ET.parse(response)
            root = tree.getroot()
                
            for item in root:
                if "NYC" in item[1].text:
                    if ("Wet" in item[0].text):
                        self.wet = True
                        break
                    if ("Snow" in item[0].text):
                        self.snowy = True
                        break
        except:
            self.wet = None
            self.snowy = None
            self.text = ""

        if (self.wet != None):
            self.text = "\nMajor Roads: Currently "
            if(self.wet and self.snowy):
                self.text += "wet/snow/ice"
            elif(self.wet):
                self.text += "wet"
            elif(self.snowy):
                self.text += "snow/ice"
            else:
                self.text += "dry"   

currentWeather = Weather([40.713, -74.006], "LGA", "7:15")
#there should be a separate function for AM Tweet and PM Tweet
tomorrowWeather = Weather([40.713, -74.006], "LGA", "17:30", 1)

#maybe should implement separate URLhandler class, with pingtest, parseJSON, and others

#This program currently is run via an external task scheduler every day, and terminates after the second tweet.
currentTime = datetime.now(pytz.timezone('US/Eastern'))
while (currentTime.hour < 18):
            schedule.run_pending()
            time.sleep(20) # wait 20 sec
            currentTime = datetime.now(pytz.timezone('US/Eastern'))
sys.exit()

    
        

 


























































