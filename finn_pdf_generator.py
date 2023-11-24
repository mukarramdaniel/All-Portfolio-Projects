from finnhub_connector import FinnhubConnector
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
import matplotlib.gridspec as gridspec
import os
import seaborn

#Estabilsh our FinnhubConnector object and use a style best for formatting in MatPlotLib
api_key = input('Paste your Finnhub API key: ')
connector = FinnhubConnector(api_key = api_key)
plt.style.use('seaborn-v0_8')

#Main function to generate the PDF report with a few helper functions within:
def generate_PDF_report(stocks, start_date, end_date, dpi, name):

    #The function below makes API calls for 'close' values of candlesticks within the given date range,
    #plots them using matplotlib and saves as .png images to our current directory to later be output
    #to our main PDF file.
    def generate_linecharts(stocks, start_date, end_date, dpi):
        for symbol in stocks:
            #Get daily candles for every stock within our given date range
            df = connector.get_stock_candles(symbol, 'D', start_date, end_date)
            df.index = pd.DatetimeIndex(df.index) #Make sure all the indices are in datetime format

            f, (a0, a1) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1]}) #Create a plot with a subplot for volume

            a0.plot(df.index, df['Close'], color='orangered', linewidth=0.75) #Plot close prices and set parameters
            a0.set_ylabel('Value (USD)', fontsize=14)

            #Block of code below takes care of annotating the low and high values within our given date range.
            y = df['Close']
            x = df.index
            new_line = '\n'

            ymax = max(y)
            xpos = np.where(y == ymax)
            xmax = x[xpos]
            xc = str(xmax)[18:26].replace('-', '/') #Gets the date of our datetime object
            a0.annotate(f'High:{new_line}${round(ymax, 2)}{new_line}{xc}', xy=(xmax, ymax), xytext=(xmax, ymax),
                        fontsize=7, va='bottom', ha='right') #Put the annotations inplace with correct parameters

            ymin = min(y)
            xpos = np.where(y == ymin)
            xmin = x[xpos]
            xc = str(xmin)[18:26].replace('-', '/')
            a0.annotate(f' Low:{new_line} ${round(ymin, 2)}{new_line} {xc}', xy=(xmin, ymin), xytext=(xmin, ymin),
                        fontsize=7, va='top', ha='right')

            plt.grid(True) #Make sure grid is on
            a0.xaxis.set_ticklabels([]) #Remove x-ticks from the first plot as they will be defined in the subplot
            a0.set_facecolor("lavender")

            #Plot the volume on our subplot and fill the space between the line and y=0 for better visualization
            a1.plot(df.index, df['Volume'], color='dodgerblue', linewidth=0.1)
            a1.fill_between(df.index, df['Volume'], color='dodgerblue')

            #Format the yticks to better visualize the volume and set color
            current_values = a1.get_yticks()
            a1.set_yticklabels(['{:,.0f}'.format(x) for x in current_values])
            a1.set_facecolor("lavender")

            #Add title and decrease empty space between plot and subplot
            f.suptitle(f"{symbol} Close Price Chart with Volume", fontsize=14)
            f.subplots_adjust(wspace=None, hspace=0.05)
            f.tight_layout()

            f.savefig(f'{symbol}-line.png', dpi=dpi) #Save the figure to our current directory with quality that will be defined later.
            plt.close()

    #Function below generates volatility graphs within the given time frame and saves as .png
    def generate_volatility_graphs(stocks, start_date, end_date, dpi):
        for symbol in stocks:
            #Generate data frames with 'close' prices, shift down by one and get log returns
            df = connector.get_stock_candles(symbol, 'D', start_date, end_date)
            df['Log returns'] = np.log(df['Close'] / df['Close'].shift())
            df['Log returns'].std()
            volatility = df['Log returns'].std() * 252 ** .5 #Get the volatility for 252 trading days in a year
            str_vol = str(round(volatility * 100, 4)) #Round the result to 4 decimal places

            #Generate the graphs, set all the parameters and save as png
            fig, ax = plt.subplots()
            df['Log returns'].hist(ax=ax, bins=50, alpha=0.7, color='navy')
            ax.set_xlabel('Log return', fontsize=14)
            ax.set_ylabel('Freq of log return', fontsize=14)
            ax.set_title(f'{symbol} Volatility from {start_date} to {end_date}: {str_vol}%', fontsize=14)
            ax.set_facecolor("oldlace")
            plt.savefig(f'{symbol}-volt.png', dpi=dpi) #Close price/volume charts end with -line and volatility end with -volt
            plt.close()

    #Establish a few variables crucial for iterating through the png files and stocks
    pdf = FPDF() #Define our fpdf object

    #Declare global lsit pointer and tracker to keep track of what our program is doing
    global list_pointer
    global tracker

    list_pointer = 0
    tracker = 0

    len_s = len(stocks)
    total_images = (len_s * 2) + 32 #Total images that will be outputted to our PDF file

    #The block of code below calculates the page on which to output text title for volatility graphs
    if len_s <= 9:
        vol_page = 2
    else:
        vol_page = int(len_s / 9) + 2

    #Defines our title base (whether to cut the list short and write 'etc.' or include the full list in our title)
    if len_s <= 4:
        title_base = str(', '.join(stocks) + f', {start_date} to {end_date}')
    else:
        title_base = str(', '.join(stocks[0:4]) + f', etc. {start_date} to {end_date}')

    #The functions below take care of all the formatting when outputting to PDF. It does not make sense to output more
    #than 9 graphs on a single page as they become hard to see. Our algorithm will take in any number of stocks, divide
    #by 9 and get the remainder. If we have 9 or less stocks, we will simply call one of the functions below. If we have
    #30 stocks for example, we will call the add9() function 3 times and the add3() function once.

    def no_remainder(type): #This function is necessary in case we have a list divisible by 9 (with a remainder of 0.) Simply move on.
        type = None
        pass

    #For this function and every one below, we add a new page to our PDF, make sure we have our pointers on track and add the generated png
    #images to the PDF file. The argument passed in tells us whether to fetch line or volatility charts, as they are formatted the same.
    #Some functions have different x, y, and width values depending on how many stocks we have, because
    #the PDF could be formatted differently (we can make images bigger if there are less stocks.) We also add 1 to each pointer
    #for each image added, and add a print statement to see how the program is progressing when we run it. The if statement in the end takes
    #care of outputting text labels on correct pages of the PDF.
    
    def add1(type):
        pdf.add_page('L') #Landscape orientation is best as the graphs are horizontal rectangles.
        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=15, y=20, w=250)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 16)

        if pdf.page_no() == 1:
            pdf.cell(275, 5, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, 10, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add2(type):
        pdf.add_page('L')
        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=0, y=55, w=145)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=145, y=55, w=145)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 18)

        if pdf.page_no() == 1:
            pdf.cell(275, 25, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, 25, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add3(type):
        pdf.add_page('L')
        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=20, w=135)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=142, y=20, w=135)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=70, y=112, w=135)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 14)

        if pdf.page_no() == 1:
            pdf.cell(275, 3, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, 3, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add4(type):
        pdf.add_page('L')
        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=20, w=135)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=142, y=20, w=135)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=112, w=135)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=142, y=112, w=135)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 14)

        if pdf.page_no() == 1:
            pdf.cell(275, 3, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, 3, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add5(type):
        pdf.add_page('L')
        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=4, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=192, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=45, y=110, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=142, y=110, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 14)

        if pdf.page_no() == 1:
            pdf.cell(275, 15, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, 15, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add6(type):
        pdf.add_page('L')
        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=4, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=192, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=4, y=110, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=110, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=192, y=110, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 16)

        if pdf.page_no() == 1:
            pdf.cell(275, 15, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, 15, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add7(type):
        pdf.add_page('L')
        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=4, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=11, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=192, y=40, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=4, y=110, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=76, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=141, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=192, y=110, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 14)

        if pdf.page_no() == 1:
            pdf.cell(275, -7, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, -4, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add8(type):
        pdf.add_page('L')

        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=11, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=11, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=190, y=11, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=76, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=76, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=190, y=76, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=45, y=141, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=142, y=141, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 14)

        if pdf.page_no() == 1:
            pdf.cell(275, -7, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, -4, f'{title_base} Volatility Graphs', 0, 1, 'C')

    def add9(type):
        pdf.add_page('L')

        global list_pointer
        global tracker

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=11, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=11, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=190, y=11, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=76, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=76, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=190, y=76, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=6, y=141, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=98, y=141, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.image(f'{stocks[list_pointer]}-{type}.png', x=190, y=141, w=90)
        list_pointer += 1
        tracker += 1
        print(f'Loaded image {tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 14)

        if pdf.page_no() == 1:
            pdf.cell(275, -7, f'{title_base} Performance PDF Report: Linecharts with Volume', 0, 1, 'C')

        elif pdf.page_no() == vol_page:
            pdf.cell(275, -4, f'{title_base} Volatility Graphs', 0, 1, 'C')

    #The dictionary below will be used for calling the necessary functions based on the length of the input list.
    #This method is more efficient than using countless 'elif' statements.
    actions = {
        0: 'no_remainder()',
        1: 'add1()',
        2: 'add2()',
        3: 'add3()',
        4: 'add4()',
        5: 'add5()',
        6: 'add6()',
        7: 'add7()',
        8: 'add8()',
        9: 'add9()',
    }

    #The function below generates 32 metric charts and plots each stock as a line on every chart.
    def generate_metric_charts(stocks, start_date, end_date, dpi):

        #Define our length=32 dictionary to rename the columns
        columns = {'bookValue': 'Book Value (USD)',
                   'ev': 'Embedded Value (USD)',
                   'cashRatio': 'Cash Ratio',
                   'currentRatio': 'Current Ratio',
                   'ebitPerShare': 'EBIT per Share (USD)',
                   'eps': 'Earnings per Share (USD)',
                   'fcfMargin': 'Free Cash Flow Margin (USD)',
                   'fcfPerShareTTM': 'Free Cash Flow Per Share (USD)',
                   'grossMargin': 'Gross Margin (%)',
                   'longtermDebtTotalAsset': 'Long Term Debt Total Asset (%)',
                   'longtermDebtTotalCapital': 'Long Term Debt Total Capital (USD)',
                   'longtermDebtTotalEquity': 'Long Term Debt Total Equity (USD)',
                   'netDebtToTotalCapital': 'Net Debt to Total Capital',
                   'netDebtToTotalEquity': 'Net Debt to Total Equity',
                   'netMargin': 'Net Margin (%)',
                   'operatingMargin': 'Operating Margin (%)',
                   'pb': 'Price-to-Book Ratio',
                   'peTTM': 'Price to Earnings TTM',
                   'pfcfTTM': 'Price to Free Cash Flow TTM',
                   'pretaxMargin': 'Pre-tax Margin (USD)',
                   'psTTM': 'Price to Sales TTM',
                   'quickRatio': 'Quick Ratio',
                   'roaTTM': 'Return on Assets (USD)',
                   'roeTTM': 'Return on Equity (USD)',
                   'roicTTM': 'Return on Invested Capital (USD)',
                   'rotcTTM': 'Return on Traded Capital (USD)',
                   'salesPerShare': 'Sales per Share',
                   'sgaToSale': 'SG&A to Sale',
                   'totalDebtToEquity': 'Total Debt to Equity',
                   'totalDebtToTotalAsset': 'Total Debt to Total Asset',
                   'totalDebtToTotalCapital': 'Total Debt to Total Capital',
                   'totalRatio': 'Total Ratio'}

        metrics = list(columns.values()) #List of values to later be used as df titles.
        start = datetime.strptime(start_date, '%Y-%m-%d') #Change the start and end dates to datetime format
        end = datetime.strptime(end_date, '%Y-%m-%d')

        dfs = [] #Empty list to be appended with data frames
        for symbol in stocks:
            df = connector.get_basic_financials(symbol)['quarterly'] #Make API calls to get quarterly financial info for each stock
            df.index = pd.DatetimeIndex(df.index) #Make sure the index is in datetime format
            df.insert(0, 'InsertedDates', df.index) #Create an additional column because we cannot use the pandas '.between' function on index
            df = df.loc[df["InsertedDates"].between(start, end)] #Only take the piece of the data frame that's between our start and end dates.
            df.drop(['InsertedDates'], axis=1, inplace=True) #Drop the extra column as it is no longer needed.
            df.reset_index(inplace=True) #Reset index because we already have our start and end dates as well as number of periods (length of df).
            df.index.rename(symbol, inplace=True) #Make sure we know which stock the df is representing by renaming index with the symbol
            dfs.append(df)

        for df in dfs:
            df.rename(columns=columns, inplace=True) #Rename columns of every data frame using our earlier dictionary.

        #The code below restructures the data frames in such a way so that instead of having many dfs- each with a stock and 32
        #metrics, we get 32 metric dfs with each column representing a stock. This way we'd be able to visually compare how the stocks
        #perform next to each other.

        to_normalize = [] #List to be appended with ready to plot data frames
        for metric in metrics: #Use the list of dictionary values defined earlier
            metric_df = pd.DataFrame() #For each create an empty df
            for df in dfs:
                try:
                    metric_df[df.index.name] = df[metric] #For each df in dfs take the specified metric column and add onto the empty df.
                except:
                    continue
            # Set index for the new df as our start date to end date with specified number of periods
            # Then make sure the index is in datetime format and rename it to keep track which metric the df represents.
            # Finally, append it to our empty list of ready to be visualized dfs.
            metric_df.index = [str(i).split(' ')[0] for i in pd.date_range(start, end, periods=len(metric_df))]
            metric_df.index = pd.DatetimeIndex(metric_df.index)
            metric_df.index.rename(metric, inplace=True)
            to_normalize.append(metric_df)

        # Book and Embedded values tend to get very large for certain stocks so we will take the cube root for
        # normalization and better visualization
        for df in to_normalize[0:2]:
            for column in df.columns:
                df[column] = df[column].apply(lambda x: x ** (1 / 3))
            df.index.rename(df.index.name + ' Normalized: y= 3√ of original', inplace=True)

        # Define a list of Matplotlib colors to iterate through
        allcolors = ['lime', 'yellow', 'coral', 'aqua', 'red', 'mediumseagreen', 'limegreen', 'royalblue',
                     'mediumorchid', 'crimson', 'lightseagreen', 'peru', 'aquamarine', 'darkorange',
                     'springgreen', 'turquoise', 'deepskyblue', 'fuchsia', 'gold', 'palegreen', 'darkturquoise',
                     'steelblue', 'yellowgreen', 'mediumspringgreen', 'plum']

        i = 0 #Tracker to make sure each .png file generated from a graph has a different file name.
        for df in to_normalize: #For each metric we plot all the stocks in our list.
            colors = allcolors.copy() * 10 #There are not that many distinctive colors so we'll take 25 and miltiply the list by 10.
            ### In an unlikely case of generating more than 250 stocks, simply change the integer above or prolong the colors list.
            ### List of available MatPlotLib colors: https://matplotlib.org/stable/gallery/color/named_colors.html
            for column in list(df.columns): #Loop to plot the line and move onto the next color
                plt.plot(df.index, df[column], color=colors[0], linewidth=2, label=column) 
                del colors[0]
            #Define the graph parameters and save the image
            plt.title(df.index.name, fontsize=14)
            plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=8.5)
            ax = plt.gca()
            ax.set_facecolor("lavender")
            plt.savefig(f'metricchart{i}.png', dpi=dpi)
            plt.close()
            i += 1

    #The function below loads metric chart to our PDF file in the correct format
    def load_metric_charts():
        pointer = 0 #Define a pointer within the scope of this function as there is always a fixed number of metric charts and we start with 0
        global tracker #Needed to print out the current image number that was loaded.

        pdf.add_page('L')

        #Load the first 5 metric charts on the first page, make the Book and Embedded value charts bigger.
        pdf.image(f'metricchart{pointer}.png', x=1, y=20, w=140)
        pointer += 1
        print(f'Loaded image {pointer + tracker}/{total_images}')

        pdf.image(f'metricchart{pointer}.png', x=144, y=20, w=140)
        pointer += 1
        print(f'Loaded image {pointer + tracker}/{total_images}')

        pdf.image(f'metricchart{pointer}.png', x=6, y=125, w=92)
        pointer += 1
        print(f'Loaded image {pointer + tracker}/{total_images}')

        pdf.image(f'metricchart{pointer}.png', x=98, y=125, w=92)
        pointer += 1
        print(f'Loaded image {pointer + tracker}/{total_images}')

        pdf.image(f'metricchart{pointer}.png', x=190, y=125, w=92)
        pointer += 1
        print(f'Loaded image {pointer + tracker}/{total_images}')

        pdf.set_font('Arial', 'B', 14)
        pdf.cell(275, 8, f'{title_base} Performance Metrics Charts', 0, 1, 'C')

        #Loads the rest of the charts using our pointer. Since we loaded the first 5 graphs and have 27 remaining, we could
        #simply create a new page and add 9 graphs to it 3 times in a row, while updating our pointer.
        for _ in range(3):
            pdf.add_page('L')

            pdf.image(f'metricchart{pointer}.png', x=6, y=11, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=98, y=11, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=190, y=11, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=6, y=76, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=98, y=76, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=190, y=76, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=6, y=141, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=98, y=141, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

            pdf.image(f'metricchart{pointer}.png', x=190, y=141, w=92)
            pointer += 1
            print(f'Loaded image {pointer + tracker}/{total_images}')

    #Function below deletes all the generated png images from the current directory after uploading them to PDF.
    def delete_images(stocks):
        for symbol in stocks:
            os.remove(f'{symbol}-line.png')
            os.remove(f'{symbol}-volt.png')
        for i in range(32):
            try:
                os.remove(f'metricchart{i}.png')
            except:
                continue

    #The PDF generation process starts. Print the time now to see how long the program takes to run
    print('Starting: ' + datetime.now().strftime('%H:%M:%S'))
    print('')

    #If the list is less than or equal to 9 we simply call addLISTLENGTH(line) which already has the formatting done,
    #by using string eval, then reset the pointer to 0 and call addLISTLENGTH(volt) which outputs volatility charts to our PDF.
    if len_s <= 9:
        print('Generating linecharts...')
        generate_linecharts(stocks, start_date, end_date, dpi)
        eval(actions.get(len_s).replace('()', "('line')"))

        list_pointer = 0

        print('Generating volatility charts...')
        generate_volatility_graphs(stocks, start_date, end_date, dpi)
        eval(actions.get(len_s).replace('()', "('volt')"))

    #If the list is longer than 9 we divide it by 9 evenly to see how many times to call the add9(type) function which creates a new
    #page every time and keeps track of which files to output. We then take the remainder of that division and call the according
    #function to output the remaining graphs. For example if our list is 40 stocks, 9 goes into 40 evenly 4 times and the remainder is 4.
    #That means we call the add9(type) function 4 times and call the add4(type) function once. Then reset the pointer to 0 and repeat the
    #same thing with volatility charts. If the remainder is 0, the no_remainder() function comes in handy.
    else:
        print('Generating linecharts...')
        generate_linecharts(stocks, start_date, end_date, dpi) #Call our generate linecharts function
        for _ in range(len_s // 9): #Outputs the part of the list divisible by 9 to out PDF
            eval(actions.get(9).replace('()', "('line')"))

        eval(actions.get(len_s % 9).replace('()', "('line')")) #Outputs the remainder of the charts

        list_pointer = 0 #Reset the pointer and repeat the same exact process for volatility charts

        print('Generating volatility charts...')
        generate_volatility_graphs(stocks, start_date, end_date, dpi) #Call the generate volatility graphs function
        for _ in range(len_s // 9):
            eval(actions.get(9).replace('()', "('volt')"))

        eval(actions.get(len_s % 9).replace('()', "('volt')"))

    #Generate metric charts and load them onto our PDF.
    print('Generating metric charts...')
    generate_metric_charts(stocks, start_date, end_date, dpi)
    load_metric_charts()

    pdf.output(f'{name}.pdf', 'F')
    delete_images(stocks) #After everything is finished we can clear the current directory of all the png files
    print('')
    print('Finished: ' + datetime.now().strftime('%H:%M:%S'))
    

'''Make sure the stocks are in a list format when passing into the function. Here are a few examples:
stocks = ['MU', 'XOM', 'TSM', 'CVX', 'SCHW', 'BABA', 'SQ', 'BA', 'INTC', 'AAPL', 'NVDA', 'V', 'NFLX', 'PYPL', 'CSCO', 'MA', 'ORCL', 'ABBV', 'AP', 'AIR', 'SAVE']
or stocks = ['GOOGL', 'META', 'AAPL', 'AMZN']
or stocks = ['ORCL']

Dates: Make sure they are in 'yyyy-mm-dd' format.
start_date = '2016-09-25'
end_date = '2017-03-20'

DPI: The quality in which an image gets uploaded to our PDF. 
List with 4 stocks at 350 dpi takes about 20 minutes to generate.
List with 21 stocks at 300 dpi takes 15 minutes to generate. 100 dpi takes 1-2 minutes.
dpi=500 takes about a minute and a half to load one image, however the quality of the PDF report would be very crisp,
So it might make sense for professional use.

Possible errors:
Sometimes the Finnhub API might not work exactly as intended and throw an error saying there is no data for a stock,
in this case simply re-running the code is often sufficient to fix it.

Below is an example of running the code: Establish the variables first then pass into the function. It will save the
PDF report into your current directory.'''


stocks = input('Enter a list of stocks separated by commas: ')
stocks = stocks.replace(' ','').split(',')
print('For high quality reports I recommend to enter dates that are at least 6 months apart')
start_date = input('Enter the start date for stock data (yyyy-mm-dd): ')
end_date = input('Enter the end date for stock data (yyyy-mm-dd): ')
dpi = input('Enter the DPI (quality of the PNG images when uploading to PDF - I recommend to test with 100 first): ')
dpi = int(dpi)
name = input('Enter the name of your PDF report: ')

generate_PDF_report(stocks, start_date, end_date, dpi, name)
