import datetime as dt
import pandas as pd
from pandas_datareader import data as pdr
import yfinance as yf
from matplotlib import style
import matplotlib.dates as mdates
import numpy as np
import mplfinance as mpf
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import os
import sys
from pandas import ExcelWriter
yf.pdr_override()

##############################################################

#I marked up this document to explain some of the code. If you have any questions on how it works...
#let me know, thanks! 

#Tyler/@ombocharts

##############################################################
#Change either to add them to the chart or remove them - automatically does the rest
enableWebbyRSI = True
enableRS = True
enableMovingAverages = True
##############################################################

#sets the moving averages and corresponding colors (ex. 8ema is 'b' - blue)
emasUsed = [8,21]
emaColors = ['b', 'm']
smasUsed = [50,200]
smaColors = ['r', 'k']
usedVolumeMA = [50]

ogStart = dt.datetime(2020,1,1) #ogstart means original start
start =  ogStart - dt.timedelta(days=2 * max(smasUsed)) #check resetDate for explaination on the 2 *
now = dt.datetime.now()
etfMode = False


stock = input("Enter your stock ticker ('quit' to exit, 'etf' to create an etf from an excel sheet): ")

def noDateGaps(df):
	global current_stock
	#Im just initialzing these - should make sense later
	hasPastIndex = False
	pastIndex = dt.datetime.now()
	for i in df.index:
		if hasPastIndex == True:#the reason this exists is bc the first datapoint doesn't have a past index - it would throw an error
			dateChange = i - pastIndex #this is the current index's date minus the previous index's date
			if dateChange > dt.timedelta(days = 10): #if the difference is over 10(arbitrary number) days, theres a gap in data
				return False
			pastIndex = i #sets the next index's past index to itself
		else: #if its the first index it sets the pastindex then moves to the next data point
			pastIndex = i
			hasPastIndex = True
	#if ther was no gaps in data in the entirety of the dataframe, noDateGaps returns true
	return True


def start_func():
	global stock,df, excelSymbols, positionSize, chartTitle, etfMode, root
	if stock == "etf":

		#this way of defining filepath you can do define through a file path directly in the code
		#filePath=r"/Users/ombocharts/Desktop/stockList.xlsx"

		#this way of defining filepath you have to open the excel file each time
		root = Tk()
		ftypes = [(".xlsm","*.xlsx",".xls")]
		ttl  = "Title"
		dir1 = 'C:\\'
		root.update()
		filePath = askopenfilename(filetypes = ftypes, initialdir = dir1, title = ttl)

		#these three lines are supposed to get rid of the annoying pop up - didn't quite work, but it hides it behind the chart atleast
		root.update()
		root.destroy()
		root.quit	

		chartTitle = str(os.path.basename(filePath)) + " Daily"

		etfMode = True
		excelSymbols = pd.read_excel(filePath) #this reads the excel file
		#excelSymbols = excelSymbols.head() #this shortens the file to the first 5 rows - good for testing
		positionSize = float(1) #you will buy positionSize dollars worth of each stock in the list (defaulted to 1), this means fractional shares
		create_etf()
	else:
		chartTitle = str(stock) + " Daily"
		df = pdr.get_data_yahoo(stock, start, now)
		if noDateGaps(df) == False:
			print("Stock had gaps from datapoints")
			error = 7/0 #I just wanted the program to restart because when it plots the chart with gaps in data its all messed up...
			#...so I had the program throw an error lol: prob better ways to get this done, but this was simple and effective



def set_start_etf_date(daysToAdd):
	global sharesToAdd, positionSize,current_stock, useStock, firstIndex, delta, daysAdded, dfDefined, iposToAdd, stock, ipoAdded
	#Reason why this exists: if you input a day that is not a trading day, the program fails
	#Solution: the function will try to calculate the amount of shares to add, 
	#if theres an error it goes an extra day in the future until it hits a trading day.
	#if mdates.date2num(current_stock[0])
	
	delta = dt.timedelta(days = daysToAdd)
	try:
		#the amount of shares to add is calculated from the start date - this means the price should be (# of stocks in etf * 100)
		sharesToAdd = positionSize / current_stock["Adj Close"][start + delta]
		firstIndex = start + delta

	except:
		#THIS SECTION IS FOR IPOS ONLY

		# if there's an error with something under try, it goes here. If the stock is an IPO there WILL be an error because
		# its trying to find the 'Adj Close' at a date prior to its existance. 
		# ex) If an IPO first datapoint was 4/01/20, and its trying to access the data from 1/01/20 there will be an error -
		# this brings us here where I keep adding a day until there isn't an error and it reached its first datapoint
		if daysToAdd < 1000:
			daysAdded = True
			set_start_etf_date(daysToAdd + 1)

			#the dataframe is initialized as the first non IPO. IPOs would make the whole chart shorter because their first datapoint
			#is past the requested start day
			#if the dataframe hasn't been initialized yet and this IPO hasn't been added to the list yet, it will do so.
			if dfDefined == False and ipoAdded == False:
				iposToAdd.append(stock)
				ipoAdded = True



def create_etf():
	global df,current_stock, ogStart, positionSize, excelSymbols, sharesToAdd, useStock,dataGap,dataNull, firstIndex,firstStock, dfDefined, iposToAdd, stock, ipoAdded, daysAdded	
	#get data for each stock and add them to the etf list with specific position size
	dfDefined = False
	ipoAdded = False
	dataNull = []
	dataGap = []
	iposToAdd = []

	for i in excelSymbols.index:
		#Just initializing these variables - should make more sense as you read
		useStock = True
		daysAdded = False
		stock=str(excelSymbols["Symbol"][i])#current stock ticker we're looking at in the excel list

		try:
			current_stock = pdr.get_data_yahoo(stock, start, now)
		except:
			dataNull.append(stock)
			continue
		set_start_etf_date(0)#go to function for explaination
		if noDateGaps(current_stock) == False:#go to function for explaination
			useStock = False

		ipoAdded = False #resetting this variable	

		if current_stock.isnull().values.any() or len(current_stock) < 1: #if there is any data in the dataframe that is null, it skips the stock
			dataNull.append(stock)
			continue #continue means goe to the next index in the for loop
		if(useStock == False):
			dataGap.append(stock)
			continue

		#If the dataframe hasn't been defined and there has been no days added to the stock (this means its not an IPO)
		#then it will define the dataframe by setting it equal to the first stock * sharesToAdd
		if dfDefined == False and daysAdded == False:
			dfDefined = True
			df = (current_stock * sharesToAdd)
		elif dfDefined == True:

			df[firstIndex:] += (current_stock[firstIndex:] * sharesToAdd)
		else:
			continue

		daysAdded = False
	for x in iposToAdd:
		#this goes through each IPO that appeared before the datafram was defined and adds it
		stock = x
		useStock = True
		current_stock = pdr.get_data_yahoo(stock, start, now)
		set_start_etf_date(0)#go to function for explaination
		if current_stock.isnull().values.any():
			dataNull.append(stock)
			#removedReasons.append("DATAPOINT WAS NULL")
			continue
		if(useStock == False):
			dataGap.append(stock)
			#removedReasons.append("IPO PROB")
			continue

		df[firstIndex:] += (current_stock[firstIndex:] * sharesToAdd)

		daysAdded = False

def setMovingAverages():
	#If this is confusing I recommend Richard Moglen's python tutorial
	global emasUsed, smasUsed, df
	for x in emasUsed:
		ema = x
		df["EMA_"+str(ema)] = df['Adj Close'].ewm(span = ema, min_periods = 0).mean()
	for x in smasUsed:
		sma = x
		df["SMA_"+str(sma)] = df['Adj Close'].rolling(window = sma, min_periods = 0).mean()
	for x in usedVolumeMA:
		volMA = x
		df["VOL_"+str(volMA)] = df['Volume'].rolling(window = volMA,min_periods = 0).mean()



def webbyRSI():
	#calculates the distance from the 21 ema, and calculates the percent from it
	global df, percentFrom21
	percentFrom21 =[]
	for row in df.index:
	 	appendMe = ((df['Adj Close'][row] - df['EMA_21'][row])/df["Adj Close"][row] * 100)
	 	if appendMe < 0:
	 		appendMe = 0
	 	percentFrom21.append(appendMe)			
	df["PERCENT_FROM_21"] = percentFrom21

def relativeStrength():
	#calculates the RS of the stock vs. SPY
	global df
	spydf = pdr.get_data_yahoo("SPY",start, now)
	stockRS = []
	for row in df.index:
		appendMe = ((df['Adj Close'][row])/spydf['Adj Close'][row])
		stockRS.append(appendMe)
	df["RS"] = stockRS

def resetDate():
	#I created this because I had issues with the moving averages - not very important

	#Explaination:
	#the dates are in trading days, so when resetting the date, adding 200 days actuallys puts the date forward...
	#further than intended b/c its setting it forward 200 trading days, not 200 calendar days

	#Fix:
	#I doubled the distance back it goes to ensure that theres enough data for the longest moving average...
	#and had a list to count how many trading days to remove (I used the length as the index: in iloc) until it hit the starting day...
	#the reason its within a range of around 6 days is because the date entered isn't necessarily on a trading day
	global df, ogStart
	removeList = []	
	for i in df.index:
		removeList.append(i)
		og = mdates.date2num(ogStart)
		passedDate = mdates.date2num(i)
		if int(passedDate >= int(og) - 3 and int(passedDate) <= int(og + 3)):
			df = df.iloc[int(len(removeList)):]
			break
	df.dropna()
def additionsAdd():
	#Sets all the extra 'addplots' to one list -> allows for more control
	global df, additions, emaColors, smaColors

	#KEY
	#panel 0 - price
    #panel 1 - volume
    #panel 2 - next indicator   


	#This variable is the index of the next panel to be added. starts at 2 - since price and volume already exists
	nextPanel = 2

	#this creates a horizontal line as long as the data frame 
	line6 = []
	line4 = []
	line2 = []
	for i in df.index:
		line6.append(6) 
		line4.append(4)
		line2.append(2)

	#creating an array to put every element from every indicator into. this is because mpf.plot only allows for one addplot
	#as a result, we must condense each seperate indicator into one array - I seperated from the start for organizational purposes
	additions =[]

	#Code for the WebbyRSI addition to the plot
	if enableWebbyRSI:
		webbyRSI_add = [
			mpf.make_addplot(df["PERCENT_FROM_21"],panel = 2, type='bar', color = 'b', mav = 10, width = .75, ylabel = "WebbyRSI"),
			mpf.make_addplot(line6,panel = nextPanel,color='r'),
		    mpf.make_addplot(line4,panel = nextPanel,color='y'),
		    mpf.make_addplot(line2,panel = nextPanel,color='g')
				] 
		for x in webbyRSI_add:
			additions.append(x)
		#since panel is being used, move to the next to set up for following indicator
		nextPanel += 1

	#Code for the Relative Strength addition to the plot
	if enableRS:
		RS_add = [
				mpf.make_addplot((df['RS']),panel=nextPanel,color='g', ylabel =  "RS")
				]
		for x in RS_add:
			additions.append(x)
		nextPanel += 1

	#Code for the moving averages addition to the plot
	if enableMovingAverages:
		movingAverages_add = []
		for x in smasUsed:
			sma = x
			movingAverages_add.append(mpf.make_addplot(df['SMA_'+str(sma)],panel = 0, color = smaColors[smasUsed.index(sma)])) #setting ema to color set at top
		for x in emasUsed:
			ema = x
			movingAverages_add.append(mpf.make_addplot(df['EMA_'+str(ema)],panel = 0, color = emaColors[emasUsed.index(ema)]))
		for x in usedVolumeMA:
			volMA = x
			movingAverages_add.append(mpf.make_addplot(df['VOL_'+str(volMA)],panel = 1))
		for x in movingAverages_add:
			additions.append(x)
		




def figures():
	global df, additions, stock, chartTitle
	#sets all the additions
	additionsAdd()

	#volume = True creates another panel (panel 1) of volume with correctly colored bars
	mpf.plot(df, type = "candle", addplot=additions, panel_ratios=(1,.25),figratio=(1,.25),figscale=1.5, style = 'blueskies', volume = True, title = chartTitle)

while stock != "quit":
	try:
		start_func()
		setMovingAverages()
		webbyRSI()
		relativeStrength()
		resetDate()
		figures()
		if etfMode:
			print("DATAPOINT WAS NULL FOR: " + str(dataNull))
			print("GAP BETWEEN DATA FOR: " + str(dataGap))
		stock = input("Enter your stock ticker ('quit' to exit, 'etf' to create an etf from an excel sheet): ")
	except:
		print("That resulted in an error")
		stock = input("Enter your stock ticker ('quit' to exit, 'etf' to create an etf from an excel sheet): ")




##############################################################

	#Thanks for reading!

##############################################################



