import praw
import pandas as pd
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import requests
from bs4 import BeautifulSoup as bs

# Instantiate Reddit API credentials
reddit = praw.Reddit(
	client_id = 'ENTER YOUR CLIENT ID',
	client_secret = 'ENTER YOUR CLIENT SECRET KEY',
	user_agent = 'ENTER YOUR USER AGENT')

# Stock ticker to search
search='GME'

# Get stock name from Finviz
url = 'https://finviz.com/quote.ashx?t='+search
header ='ENTER YOUR WEB BROWSER USER AGENT'
r = requests.get(url,headers={'User-Agent':header})

html = bs(r.text, 'lxml')
wc = html.find('table', {'class':'fullview-title'})
wc = wc.find('a', {'class':'tab-link'})
name = wc.get_text()

words_to_remove = [' Inc.',',','The ',' Company',' Corporation',' Group',' Holdings',' Holding',' Limited',' Incorporated', ' Corp.','.com',' Companies', ' Investments', ' Investment']
for word in words_to_remove:
	name = name.replace(word,'')
print('Stock name: '+name)

# List of popular subreddits on stocks
subreddits = ['investing', 'stocks', 'wallstreetbets','StockMarket', 'Stock_Picks', 'SecurityAnalysis', 'Daytrading', 'RobinHood','worldnews']

# Initiate variables to cache the data
# List to cache comment data
comment_cache = []

# Dictionaries to cache submission data
sub_cache = {
			'ID':[],
			'User':[],
			'Title':[],
			'Body':[],
			'Date/time':[],
			'Upvote':[],
			'Num_comments':[],
			'URL':[]
			}

# Define time range i.e. the last 24 hours in this case
time_threshold=datetime.now()-timedelta(days=1)

# Crawl each subreddit to retrieve data
for subreddit in subreddits:

	submissions = reddit.subreddit(subreddit).new(limit=None)

	for n in submissions:
		# Only accept submission which is not deleted, and the stock ticker or its name is in the submission, within the last 24 hours
		if n.author != '[deleted]' and (datetime.fromtimestamp(n.created_utc)>time_threshold) and (search.lower() in n.title.lower() or name.lower() in n.title.lower()):
			sub_cache['ID'].append(n.id)
			sub_cache['User'].append(n.author)
			sub_cache['Title'].append(n.title)
			sub_cache['Upvote'].append(n.score)
			sub_cache['Date/time'].append(datetime.fromtimestamp(n.created_utc))
			sub_cache['URL'].append(n.url)
			sub_cache['Num_comments'].append(n.num_comments)
			sub_cache['Body'].append(n.selftext)

			n.comments.replace_more(limit=None)
			for comment in n.comments.list():
				# Only accept comments which have more or less than 2 upvotes, not deleted, and are not from moderators
				if (comment.score> 2 or comment.score< -2) and (comment.body != '[deleted]' and comment.body != '[removed]') and (comment.author.is_mod == False):
					comment_cache.append(comment.body)



# Clean up text to remove hyperlink & username
def cleantext(txt):
	txt = re.sub(r'\n',' ', txt)
	txt = re.sub(r'r/[_A-Za-z0-9]+','',txt)
	txt = re.sub(r'https?:\/\/\S+', '', txt)
	txt = ' '.join(txt.split())
	return txt

sub_cache_clean = [cleantext(i) for i in sub_cache['Title']]
comment_cache_clean = [cleantext(i) for i in comment_cache]


# Perform sentiment analysis
vader = SentimentIntensityAnalyzer()
sub_score = []
sub_sentiment = []
com_score = []
com_sentiment = []

# Sentiment analysis on submission text
for i in sub_cache_clean:
	compound = vader.polarity_scores(i)['compound']
	sub_score.append(compound)
	if compound	>0.05:
		sub_sentiment.append('Positive')
	elif compound < -0.05:
		sub_sentiment.append('Negative')
	else:
		sub_sentiment.append('Neutral')

sub_cache['Score'] = sub_score
sub_cache['Sentiment'] = sub_sentiment

# Sentiment analysis on comment text
for i in comment_cache_clean:
	compound = vader.polarity_scores(i)['compound']
	com_score.append(compound)
	if compound	>0.05:
		com_sentiment.append('Positive')
	elif compound<-0.05:
		com_sentiment.append('Negative')
	else:
		com_sentiment.append('Neutral')

# Convert to dataframe
df = pd.DataFrame(sub_cache)
pd.set_option('display.expand_frame_repr', False)
print('Submission List:')
print(df.head())
print('===============================================================================================')

df_comment = pd.DataFrame({'Comment':comment_cache, 'Score':com_score, 'Sentiment':com_sentiment})
print('Comment List:')
print(df_comment.head())
print('===============================================================================================')

df_pos = df[df['Sentiment']=='Positive']
df_neg = df[df['Sentiment']=='Negative']
df_neu = df[df['Sentiment']=='Neutral']

df_comment_pos = df_comment[df_comment['Sentiment']=='Positive']
df_comment_neg = df_comment[df_comment['Sentiment']=='Negative']
df_comment_neu = df_comment[df_comment['Sentiment']=='Neutral']


try:
	v = {'Positive':round((df_pos.shape[0]+df_comment_pos.shape[0])*100/(df.shape[0]+df_comment.shape[0]),2),
		 'Negative':round((df_neg.shape[0]+df_comment_neg.shape[0])*100/(df.shape[0]+df_comment.shape[0]),2),
		 'Neutral':round((df_neu.shape[0]+df_comment_neu.shape[0])*100/(df.shape[0]+df_comment.shape[0]),2) 	
		}

except ZeroDivisionError:
	print('No submission on {} for the past 24 hours.'.format(search))


print('Total submission count of {}: {}'.format(search,len(sub_cache['ID'])))
print('Total comment count of {}: {}'.format(search,len(comment_cache)))
print('% Positive: ',v['Positive'], '\n%Negative: ',v['Negative'], '\n%Neutral: ',v['Neutral'] )
print('Overall Reddit sentiment of {} for the last 24 hours is mostly {} ({}%).'.format(search, max(v, key=v.get), v[max(v, key=v.get)]))



