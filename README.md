# ShouldIBike

Python Bot that creates NYC bike commute forecasts and publishes them to Twitter bi-daily. Currrently running on Twitter at @ShouldIBike

This bot uses the PyOWM API (Python Open Weather Map) for the main weather data, tweepy (python Twitter API), the 511NY API (New York State road conditions), 
the MyTSA Web Service API (for sunset/sunrise), and pulls NYC subway info from the MTA via an XML feed. 

This program currently is run via an external task scheduler every day, and terminates after the second tweet.

This is a constant work in progress, so any code optimization/other additions would be enthusiastically welcomed.


