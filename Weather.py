import math, pandas as pd, pytz
from datetime import datetime, timedelta
#Original Modules below, please make sure they're in right dir and importable
import ExternalConnection, RoadConditions, SunTimes
import PyOWMWeathercodes as wc

#[numeric end month of possible winter conditions, numeric start of possible winter conditions]. Define both as 0 if winter conditions are nonexistent in locale.
WINTERMONTHS = [4,10]
WIND_MAP = ["N","NE","E","SE","S","SW","W","NW","N"]
SEASONABLE_CSV_PATH = 'nycavgweather.csv'
SEASONABILITY = [-5, 5] #Set range of what a seasonable temp variance is. This is just my opinion.

class Weather(object):
	def __init__(self, location, airport, day=0):
		#mandatory parameters
		self.location = location
		self.airport = airport
		#misc
		self.attire = ""
		#rain-related attributes
		self.littleRain = False
		self.heavyRain = False
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
		self.lowDiurnalRange = False
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
					if (snowStatus >= 6.35):
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
		self.lowDiurnalRange = True if (abs(self.eveTemp - self.mornTemp) < 10) else False
		
	def getRain(self):
		if (self.weatherReading.get_rain()): 
			rain = self.weatherReading.get_rain() 
			if ('all' in rain):
				rainStatus = rain['all']
				traceRainCutoff = 7.62
				heavyRainCutoff = 18

				if (traceRainCutoff < rainStatus < heavyRainCutoff):
					self.rainText = format(self.mmToIn(rainStatus), '.1f') + '" rain'
					self.rain = True
				elif (rainStatus >= heavyRainCutoff):
					self.rainText = format(self.mmToIn(rainStatus), '.1f') + '" rain'
					self.rain = True
					self.heavyRain = True
				else:
					self.littleRain = True
					self.rain = False
		else: 
			self.littleRain = True
			self.rainText = "no rain"
			self.rain = False
	  
	def interpretWeatherCode(self):
		#pull weather code and make hghghghuman-readable
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

		if self.hiTemp < 25:
			self.tempStatus = "bitter cold"
		elif self.hiTemp >= 86:
			self.tempStatus = "hot"
		elif (self.avgCommuteTemp < 18):
			self.tempStatus = "bitter cold"
		elif (18 <= self.avgCommuteTemp < 26):
			self.tempStatus = "frigid"
		elif (26 <= self.avgCommuteTemp < 41):
			self.tempStatus = "cold"
		elif (41 <= self.avgCommuteTemp < 52):
			self.tempStatus = "brisk"
		elif (52 <= self.avgCommuteTemp < 64):
			self.tempStatus = "mild"
		elif (64 <= self.avgCommuteTemp < 73):
			self.tempStatus = "pleasant temps"
		elif (73 <= self.avgCommuteTemp <= 79):
			self.tempStatus = "warm"
		elif (self.avgCommuteTemp > 79):
			if self.lowDiurnalRange:
				self.tempStatus = "warm"
			else:
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