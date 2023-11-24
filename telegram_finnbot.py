from telegram import Update
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters
from datetime import date
from dateutil.relativedelta import relativedelta
import random

# import FinnhubConnector and establish the the object. Then enter your token (telegram bot API key).
from finnhub_connector import FinnhubConnector

api_key = input('Paste your Finnhub API key: ')
connector = FinnhubConnector(api_key=api_key)

TOKEN = input('Paste your Telegram Bot Token: ')

# This function gives all the instructions on how to work with the bot. In order to call it run the code and send the bot the below message:
# /hello
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'''Hello {update.effective_user.first_name}, and welcome to the Finnhub Connector Bot! Whenever you\'re sending commands, \
you have to make sure the code is up and running. Down below are instructions on how to talk to me.
I operate on simple two letter commands followed by a stock symbol. Always make sure that all the letters are capital
and the two letter command is followed by a space, followed by the symbol of your chosen stock (which could have
any amount of letters). Here is the list of commands with examples: 

CQ: Current Quote. Makes an API call to the FinnhubConnector and return the real time price of the stock with a few
additional parameters. Example:
CQ TSLA

RS: Random stock. There are over 28000 different symbols on the stock exchange, and this command returns a randomly picked \
symbol. Simply input->
RS

LU: Look Up a stock. Returns queried results of a search in a small data frame. Use this command if you don't remember the exact \
name/symbol of a stock or a company. Example:
LU googl

LN: Latest News. Get the latest pieces of news of a stock with headlines and links based on \
inputting a symbol. Example:
LN META

PY: Past Year performance. Get the 52-week high, low, revenue, daily return values, etc. Of a stock. Example:
PY BRK.A

LQ: Last Quarter's values. Get the last quarters book value, cash ratio, gross margin, etc. of a stock. Example:
LQ CAT

ES: Earnings Surprises. Get the expected and actual earnings of a company with percentages, for the last 4 quarters. Example:
ES MSFT

DC, WC or MC. Daily, Monthly or Weekly candles of a stock. DC returns the daily candles for every trading day starting from a month\
before the current date. WC returns a list of weekly candles starting from 6 months before the current date. MC returns\
monthly candles starting from 3 years before the current date. Examples:
DC FRC
WC ST
MC GOOGL''')

# Create a few functions that will later be called from our main bot function. These functions make Finnhub API calls and
# return info in the most comfortable text format for the Telegram App cellphone view. Function below gets the current quote
# of a desired stock.
def current_quote(symbol):
    df = connector.get_current_quote(f'{symbol}').iloc[0]
    return str(dict(df)).replace(', ', '\n').replace('\'', '').replace('{', '').replace('}', '')

#Create a list of all the stocks to be used in our random.choice function if we'd like to choose a random symbol.
stocks = connector.get_north_american_stocks()['Symbol']

# Returns the results of a search query when we are trying to look up a stock or a company.
def look_up(query):
    df = connector.look_up_stock(query)
    df['Description'] = df['Description'].apply(lambda x: x + ':')
    df['Symbol'] = df['Symbol'].apply(lambda x: x + ';#')

    x = list(df['Description'])
    y = list(df['Symbol'])

    for i, v in enumerate(y):
        x.insert(2 * i + 1, v)
    return str(x).replace('\'', '').replace(',', '').replace(']', '').replace('[', '').replace('# ', '\n').replace(';#',
                                                                                                                   '')
# Returns the latest news of a stock with headlines and links.
def get_latest_news(symbol):
    current_date = date.today()
    aweekago = current_date - relativedelta(weeks=1)
    current_date = str(current_date)
    aweekago = str(aweekago)

    df = connector.get_company_news(symbol, aweekago, current_date).tail(10)
    df['URL'] = df['URL'].apply(lambda x: x + '(())')
    df['Headline'] = df['Headline'].apply(lambda x: x + ' -> ')
    x = list(df['Headline'])
    y = list(df['URL'])

    for i, v in enumerate(y):
        x.insert(2 * i + 1, v)
    return str(x).replace('(())', '\n\n').replace('\'', '').replace('\"', '').replace(', ', '').replace(']',
                                                                                                        '').replace('[',
                                                                                                                    '').replace(
        r'\xa0', '').strip()

# Returns the 52-week performance metrics of the desired stock.
def past_year_performance(symbol):
    df = connector.get_basic_financials(symbol)['past_year']
    df['param'] = df.index
    df['param'] = df['param'].apply(lambda x: x + ':')
    df['metric'] = df['metric'].apply(lambda x: str(x) + ';')
    x = list(df['param'])
    y = list(df['metric'])

    for i, v in enumerate(y):
        x.insert(2 * i + 1, v)

    return str(x).replace('\'', '').replace(', ', '').replace('[', '').replace(']', '').replace(';', '\n').replace(':',
                                                                                                                   ': ')
# Returns the last quarter's performance stats of a company.
def last_quarter(symbol):
    stock = connector.get_basic_financials(symbol)['quarterly']
    x = [i + ': ' for i in list(stock.columns)]
    y = [str(i) + ';' for i in list(stock.iloc[-1])]

    for i, v in enumerate(y):
        x.insert(2 * i + 1, v)

    return str(x).replace('\'', '').replace(', ', '').replace('[', '').replace(']', '').replace(';', '\n').strip()

# Returns earnings surprises with percentages of expected and actual earnings of a stock.
def earnings_surprises(symbol):
    df = connector.get_earnings_surprises(symbol)
    df.insert(0, 'Period', df.index)
    df.drop(['Symbol', 'Year'], axis=1, inplace=True)

    surprises = []
    for i in range(len(df)):
        surprises.append(
            str(dict(df.iloc[i])).replace('{', '').replace('\'', '').replace(', ', '\n').replace('}', '\n\n'))

    return str(surprises).replace('[', '').replace(']', '').replace('\'', '').replace(', ', '').replace('\\n',
                                                                                                        '\n').strip()
# Establishes the current date (whenever the function was called) and returns daily candles of a stock starting one month
# from that date.
def daily_candles(symbol):
    current_date = date.today()
    amonthago = current_date - relativedelta(months=1)
    current_date = str(current_date)
    amonthago = str(amonthago)

    df = connector.get_stock_candles(symbol, 'D', amonthago, current_date)
    df.insert(0, 'Date', df.index)
    df['Date'] = df['Date'].apply(lambda x: x.split(' ')[0])
    df.drop(['Status'], axis=1, inplace=True)
    candles = []
    for i in range(len(df)):
        candles.append(dict(df.iloc[i]))

    return str(candles).replace('\'', '').replace('[', '').replace('{', '').replace(']', '').replace('}, ',
                                                                                                     '\n\n').replace(
        '}', '')

# Returns monthly candles starting from 3 years ago. (From the date function was called).
def monthly_candles(symbol):
    current_date = date.today()
    threeyearsago = current_date - relativedelta(years=3)
    current_date = str(current_date)
    threeyearsago = str(threeyearsago)

    df = connector.get_stock_candles(symbol, 'M', threeyearsago, current_date)
    for column in ['Close', 'High', 'Low', 'Open']:
        df[column] = df[column].apply(lambda x: round(x, 2))
    df.insert(0, 'Date', df.index)
    df['Date'] = df['Date'].apply(lambda x: x.split(' ')[0])
    df.drop(['Status'], axis=1, inplace=True)
    candles = []
    for i in range(len(df)):
        candles.append(dict(df.iloc[i]))

    return str(candles).replace('\'', '').replace('[', '').replace('{', '').replace(']', '').replace('}, ',
                                                                                                     '\n\n').replace(
        '}', '')

# Returns weekly candles starting from 6 months before the current date.
def weekly_candles(symbol):
    current_date = date.today()
    sixmonthsago = current_date - relativedelta(months=6)
    current_date = str(current_date)
    sixmonthsago = str(sixmonthsago)

    df = connector.get_stock_candles(symbol, 'W', sixmonthsago, current_date)
    for column in ['Close', 'High', 'Low', 'Open']:
        df[column] = df[column].apply(lambda x: round(x, 2))
    df.insert(0, 'Date', df.index)
    df['Date'] = df['Date'].apply(lambda x: x.split(' ')[0])
    df.drop(['Status'], axis=1, inplace=True)
    candles = []
    for i in range(len(df)):
        candles.append(dict(df.iloc[i]))

    return str(candles).replace('\'', '').replace('[', '').replace('{', '').replace(']', '').replace('}, ',
                                                                                                     '\n\n').replace(
        '}', '')

# Main asynchronous function what would be taking all the commands and calling our helper functions, after which it'll be
# automating replies to our user.
async def main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    #Split the message into the command (first two letters), and the symbol (all the letters after the space).
    message = update.message.text
    command = message[0:2]
    symbol = message[3::]

    # Call the right functions depending on the command and reply back. In this specific scenario it's best to use elif
    # statements as opposed to dictionaries, because dictionaries would make countless API calls.
    try:
        if command == 'CQ':
            await update.message.reply_text(current_quote(symbol))

        elif message == 'RS':
            await update.message.reply_text(f'Result: {random.choice(stocks)}')

        elif command == 'LU':
            await update.message.reply_text(f'Description: Symbol; -> Next\n{look_up(symbol)}')

        elif command == 'LN':
            await update.message.reply_text(get_latest_news(symbol))

        elif command == 'PY':
            await update.message.reply_text(past_year_performance(symbol))

        elif command == 'LQ':
            await update.message.reply_text(last_quarter(symbol))

        elif command == 'ES':
            await update.message.reply_text(earnings_surprises(symbol))

        elif command == 'DC':
            await update.message.reply_text(daily_candles(symbol))

        elif command == 'MC':
            await update.message.reply_text(monthly_candles(symbol))

        elif command == 'WC':
            await update.message.reply_text(weekly_candles(symbol))

        else:
            await update.message.reply_text(f'ERROR: "{message}" IS NOT A VALID COMMAND')

    # If there is an ValueError, that means the Finnhub API coudn't find any data for a symbol. KeyError is extremely rare
    # and means that we have a free account and only paid members have access to the resource we are trying to access.
    except ValueError:
        await update.message.reply_text(f'ERROR: COULDN\'T FIND ANY DATA FOR "{symbol}"')

    except KeyError:
        await update.message.reply_text(f'ERROR: YOU DON\'T HAVE API ACCESS TO: "{symbol}"')

# Build our app and establish callbacks
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main))

# Continuously run the app
print('')
print('Your app is now running! Go to the chat and send the bot a message: /hello \nThis will give you a list'
      ' of available commands. Follow the instructions to get information for any stocks you want. Enjoy!')
app.run_polling()
print('')
print('##### Connection Closed #####')
