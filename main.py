import csv, datetime, json, math, os, pandas as pd, pytz, sys
from datetime import datetime, timedelta
#import pandas as pd
#Original Modules below, please make sure they're in right dir and importable
import PyOWMWeathercodes as wc
import ExternalConnection, Images, Recommendation, RoadConditions, Subway, SunTimes, TimeKeeper
#from Images import Image

#Global, easy to find VIP variables
GPSLOCATION = [40.79, -73.96]
#[numeric end month of possible winter conditions, numeric start of possible winter conditions]. Define both as 0 if winter conditions are nonexistent in locale.
WINTERMONTHS = [4,10]
AMTWEETTIME = "07:40"
PMTWEETTIME = "17:00"
PUBLISH = True
AIRPORT = "LGA"
SEASONABLE_CSV_PATH = 'nycavgweather.csv'
WORKING_DIRECTORY = '/home/pi/Documents/shouldibike/'
IMAGES_DIRECTORY = '/images/'
IMAGES_TO_PULL = ["http://207.251.86.238/324", "MhnBrEntr", "Manhattan Bridge Entrance"], ["http://207.251.86.238/cctv14.jpg", "BKBr3", "Brooklyn Bridge Path"], ["http://207.251.86.238/361", "wbbBrEntr", "Williamsburg Bridge Entrance"]
SEASONABILITY = [-5, 5] #Set range of what a seasonable temp variance is. This is just my opinion.
WIND_MAP = ["N","NE","E","SE","S","SW","W","NW","N"]

"""
model - call TimeKeeper*Singleton* to count time
			TweetJob (create payload and schedule)	->	
				TimeKeeper.Schedule() 
				Forecaster() -> 
				Weather ->
					Weather.update()
					Recommendation (new)
			TweetPublisher*Singleton* to publish
			ExternalConnection*Singleton* - pingTest and APIConnect		

"""

class Weather(object):
	def __init__(self, location, airport, day=0):
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
		self.wet = False
		self.snowy = False
		self.snow = False
		self.winter = self.isWinter()
		#wind-related attributes
		self.windy = False
		self.windString = ""
		self.weatherReading = ""
		self.weatherStatus = "undeclared"
		self.humidity = ""
		self.forecastTime = datetime.utcnow()
		self.today = True
		print(str(self.forecastTime))
		if(day):
			#if day not stated, Tweet is for today. Otherwise, increment days by number specified
			incrementedDays = int(day) #is it necessary to cast as an int?
			self.today = False
			self.forecastTime = datetime.now() + timedelta(days=incrementedDays)
			self.forecastTime = datetime(self.forecastTime.year, self.forecastTime.month, self.forecastTime.day, 
										6, 0, 0, 0,tzinfo=pytz.timezone('US/Eastern'))
		else:
			self.forecasttime = datetime(self.forecastTime.year, self.forecastTime.month, self.forecastTime.day, self.forecastTime.hour, 0,0,0, tzinfo=pytz.timezone('US/Eastern'))
			self.forecastTime += timedelta(hours=6)
			#error will be thrown without 6 hour incrementation - it was tested, and this was the minimum 
			#incrementation that could be used, without an error. ¯\_(?)_/¯
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
				self.owm = ExternalConnection.ExternalConnection.getInstance().returnOWMConnection()
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
		#self.getHumidity()
		self.getSunTimes()
		if (self.winter and self.today):
			roads = RoadConditions.RoadConditions()
			self.winterRoadConditions = roads.text
			self.snowy, self.wet = roads.snowy, roads.wet
		self.interpretWeatherCode()
		self.isSeasonable()
		self.interpretTemp()
	
	def isWinter(self):
		if (WINTERMONTHS[1] > datetime.now().month > WINTERMONTHS[0]):
			return False
		else:
			return True
		
	def mmToIn(self, mm):
		return (mm * 0.0393701)

	def getSunTimes(self):
		self.sunriseTime, self.sunsetTime = SunTimes.SunTimes(self).getSunTimes()

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
				
	def getHumidity(self):
		self.humidity = str(self.weatherReading.get_humidity()) + "% humidity"
		

	def getWind(self):
		if (self.weatherReading.get_wind()):
			wind = self.weatherReading.get_wind()
			if ('speed' in wind):
				ws = (wind['speed']) * 2.23694 #convert m/s to mph
				if (ws >= 15):
					self.windy = True
				windSpeed = math.ceil(ws)
				if ('deg' in wind):
					dir = wind['deg']
					windDir = self.getWindDirection(dir)
					if windDir:
						self.windString = "{} mph {} wind".format(windSpeed, windDir)
					else:
						self.windString = "{} mph wind".format(windSpeed)
			else: 
				self.windString = "no wind"
	
	def getWindDirection(self, degrees):
		if (0 <= degrees <= 360):
			try:
				direction = round(degrees/45)
				return WIND_MAP[direction]
			except:
				return None
		else:
			return None		
		
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
		self.elapsedDays =	elapsedDate.days
		#if leap year, use 365th day of year instead of 366th
		if self.elapsedDays >= 363:
			self.elapsedDays == 362

	def dayOfWeek(self):
		dayMapLong = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
		dayMapShort = ["Mon", "Tues", "Wed", "Thurs", "Fri", "Sat", "Sun"]
		self.dayofWeek = {}
		self.dayofWeek["short"] = dayMapShort[self.forecastTime.weekday()]
		self.dayofWeek["long"] = dayMapLong[self.forecastTime.weekday()]
		return self.dayofWeek
		
	def isSeasonable(self):
		fileOpened = True
		self.getElapsedDays()
		#Should have one class for FileConnection
		try:
			data = pd.read_csv(SEASONABLE_CSV_PATH)
		except:
			fileOpened = False
		if (fileOpened):
			self.historicAvgTemp = data.iloc[(self.elapsedDays -1),0] #data.iloc[(self.elapsedDays -1),1] <- this was referencing an old file that had an extra column
			self.avgDifference = self.avgTemp - self.historicAvgTemp
			if (SEASONABILITY[0] < self.avgDifference < SEASONABILITY[1]):
				self.seasonable = True
			else:
				self.seasonable = False
				if (self.avgDifference >= SEASONABILITY[1]):
					self.unseasonablyWarm = True
				else:
					self.unseasonablyCold = True 
		else:
			self.seasonable = True
			self.unseasonablyWarm = False
			self.unseasonablyCold = False

class TweetPublisher(object): 
	def __init__(self, tweetContents, images=None):
		self.tweetContents = tweetContents
		if (images):
			self.images = images
		else:
			self.images = None
		self.tweetError = False
		self.publishTweet()
		
	def publishTweet(self):
		print(self.tweetContents)
		if(PUBLISH):
			try:
				self.ec = ExternalConnection.ExternalConnection.getInstance()
				twitter = self.ec.returnTwitterConnection()
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
class TweetJob(object):
	def __init__(self, argument, tweetTime):
		#self.argument, self.tweetTime = argument, tweetTime
		self.truncationAttempted = False
		self.punctuation = ""
		self.tweetContents = ""
		self.tk = TimeKeeper.TimeKeeper.getInstance()
		func = getattr(self, argument)
		self.tk.schedule(func, tweetTime)
		print("Successfully scheduled " + argument)
		#declare suntimes variables 
		
	def tweetLength(self):
		self.tweetLength = len(self.tweetContents)
	def AMTweet(self):
		self.weatherObj = Weather(GPSLOCATION, AIRPORT)
		self.rec = Recommendation.Recommendation(self.weatherObj)
		self.formTweet()
		TweetPublisher(self.tweetContents)
	def PMTweet(self):
		self.weatherObj = Weather(GPSLOCATION, AIRPORT, 1)
		self.rec = Recommendation.Recommendation(self.weatherObj)
		self.formTweet()
		TweetPublisher(self.tweetContents)
	def WeekTweet(self):
		tempTweet = ""
		for x in range (1,6):
			self.weatherObj = Weather(GPSLOCATION, AIRPORT, x)
			self.rec = Recommendation.Recommendation(self.weatherObj)
			tempTweet += self.weatherObj.dayofWeek["short"] + "- " + str(self.rec.rating) + "/" 
			tempTweet += self.weatherObj.weatherStatus + "/Morn " + str(math.ceil(self.weatherObj.mornTemp)) + "°F/Eve " + str(math.ceil(self.weatherObj.eveTemp)) + "°F"
			if(self.rec.weatherEmoji):
				tempTweet += self.rec.weatherEmoji + "\n"
		self.tweetContents = "THIS WEEK'S CONDITIONS:\n" + tempTweet
		self.addHashTag()
		TweetPublisher(self.tweetContents)
	def WeekendTweet(self):
		tempTweet = ""
		for x in range (1,3):
			self.weatherObj = Weather(GPSLOCATION, AIRPORT, x)
			self.rec = Recommendation.Recommendation(self.weatherObj)
			tempTweet += self.weatherObj.dayofWeek["long"] + "- " + str(self.rec.rating) + "/" 
			tempTweet += self.weatherObj.weatherStatus + "/Morn " + str(math.ceil(self.weatherObj.mornTemp)) + "°F/Eve " + str(math.ceil(self.weatherObj.eveTemp)) + "°F"
			if ((self.weatherObj.rainText) and (self.weatherObj.weatherStatus != "trace rain")):
				tempTweet += "/" + self.weatherObj.rainText
			if(self.rec.weatherEmoji):
				tempTweet += self.rec.weatherEmoji + "\n"
			#Get the emoji here
		self.tweetContents = "THIS WEEKEND: \n" + tempTweet
		self.addHashTag()
		TweetPublisher(self.tweetContents)
	def ImageTweet(self):
		# This should also be triggered in the PM if the weather is currently bad, or if it WAS bad during the AM
		self.paths = []
		for item in IMAGES_TO_PULL:
			image = Images.Image(item)
			if(image.isValid):
				self.tweetContents += image.description + ", "
				self.paths.append(image.localPath)
		if (self.tweetContents):
			#If we actually successfully pulled anything down
			self.tweetContents = "Current views of " + self.tweetContents
			self.tweetContents += " via DOT traffic camera feeds."
			#Could have a try/catch here
			self.addHashTag()
			TweetPublisher(self.tweetContents, self.paths)
	def recommendation(self):
		self.rec = Recommendation.Recommendation(self.weatherObj)
	def printTweet(self):
		print(self.tweetContents)
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
		
	def getTweetLength(self):
		self.tweetLength = len(self.tweetContents)
	def formTweet(self):
	#Have a short version
		if (self.rec.rating == "OPTIMAL"):
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
		print("sunriseTime = " + str(self.weatherObj.sunriseTime))
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
				
		
		self.getTweetLength()
		
		if (self.tweetLength > 270 and not self.truncationAttempted):
			self.truncate()
			self.formTweet()
			
		self.addHashTag()
			
	def addHashTag(self):
		self.getTweetLength()
		if (self.tweetLength <= 271):
			self.tweetContents += "\n#bikenyc"
			
	def truncate(self):
		self.getTweetLength()
		self.tweetContents = ""
		self.weatherObj.weatherEmoji = ""
		if(self.tweetLength > 276):
			self.rec.rating2 = ""
		self.truncationAttempted = True
		
#MAIN GOES HERE
#weekend should not use commute times for formulation. should include peak of day
timekeeper = TimeKeeper.TimeKeeper()
ec = ExternalConnection.ExternalConnection()


TweetJob("AMTweet", AMTWEETTIME)
if (timekeeper.dayofWeek["long"] in ["Friday"]):
	TweetJob("WeekendTweet", PMTWEETTIME)
elif (timekeeper.dayofWeek["long"] in ["Sunday"]):
	TweetJob("WeekTweet", PMTWEETTIME)
else:
	TweetJob("PMTweet", PMTWEETTIME)
TweetJob("ImageTweet", AMTWEETTIME)
timekeeper.runJobs()

