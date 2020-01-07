import json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime

class SunTimes(object):
	def __init__(self, Weather):
		#print("SunTimes instantialized with" + str(Weather))
		self.WeatherObj = Weather
		self.airport = self.WeatherObj.airport
		self.today = self.WeatherObj.today
		self.forecastTime = self.WeatherObj.forecastTime
		self.sunriseTime = ""
		self.sunsetTime = ""
		
	def parseJSON(self, url, string):
		response = urllib.request.urlopen(url)
		str_response = response.read().decode('utf-8')
		JSONdata = json.loads(str_response)
		if (string in JSONdata):
		   return (JSONdata[string])
		else:
		   return None

	def formatTime(self, time):
		formattedTime = datetime.strptime(time,'%I:%M:%S %p')
		formattedTime = formattedTime.strftime('%H:%M')
		return formattedTime
   
	def getSunTimes(self):
		URL = "https://apps.tsa.dhs.gov/MyTSAWebService/GetEventInfo.ashx?&output=json&airportcode=" + self.airport
		sunriseURL = URL + "&eventtype=sunrise"
		sunsetURL = URL + "&eventtype=sunset"
		if (not self.today):
			tempTime = self.forecastTime.strftime('%m/%d/%y')
			APIDateString = "&eventdate=" + tempTime #"{self.forecastTime:%m/%d/%y}"
			sunriseURL += APIDateString
			sunsetURL += APIDateString
		try:
			self.sunriseTime = self.parseJSON(sunriseURL, "Sunrise")
			self.sunsetTime = self.parseJSON(sunsetURL, "Sunset")
			self.sunriseTime = self.formatTime(self.sunriseTime)
			self.sunsetTime = self.formatTime(self.sunsetTime)
		except:
			#keep self.sunriseTime and self.sunsetTime empty
			print("Could not get sunset data\n")
		return [self.sunriseTime, self.sunsetTime]
