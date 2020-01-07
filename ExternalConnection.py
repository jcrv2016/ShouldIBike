import os, pyowm, subprocess, tweepy
#This contains the API keys
from credentials import *

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
