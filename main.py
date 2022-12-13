#Original Modules below, please make sure they're in right dir and importable

from ExternalConnection import ExternalConnection
from Tweet import TweetJob
from TimeKeeper import TimeKeeper

import sys

#Global, easy to find VIP variables
#Get command-line times, if they exist

if (sys.argv[1], sys.argv[2]):
	AMTWEETTIME = sys.argv[1]
	PMTWEETTIME = sys.argv[2]
else:
	AMTWEETTIME = "07:40"
	PMTWEETTIME = "17:00"


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
		
#MAIN GOES HERE
#weekend should not use commute times for formulation. should include peak of day

timekeeper = TimeKeeper()
ec = ExternalConnection()

TweetJob("AMTweet", AMTWEETTIME)
if (timekeeper.dayofWeek["long"] in ["Friday"]):
	TweetJob("WeekendTweet", PMTWEETTIME)
elif (timekeeper.dayofWeek["long"] in ["Sunday"]):
	TweetJob("WeekTweet", PMTWEETTIME)
else:
	TweetJob("PMTweet", PMTWEETTIME)
TweetJob("ImageTweet", AMTWEETTIME)
timekeeper.runJobs()

