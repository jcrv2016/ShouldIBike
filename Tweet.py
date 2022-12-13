import math
import ExternalConnection, Images, Recommendation, Subway, TimeKeeper
from Weather import Weather

IMAGES_TO_PULL = ["https://jpg.nyctmc.org/324.jpg", "MhnBrEntr", "Manhattan Bridge Entrance"], ["https://jpg.nyctmc.org/14.jpg", "BKBr3", "Brooklyn Bridge Path"], ["https://511ny.org/map/Cctv/4616625--17", "qbbPath", "Queensboro Bridge Path"], ["https://511ny.org/map/Cctv/4616622--17", "qbbEntr", "Queensboro Bridge Queens Entrance"]
GPSLOCATION = [40.79, -73.96]
AIRPORT = "LGA"
PUBLISH = True

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
