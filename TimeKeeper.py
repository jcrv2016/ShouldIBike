import pytz, schedule, sys, time
from datetime import datetime

EXITTIME = 23

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
