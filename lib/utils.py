import sys
import gdata
import gdata.youtube.service

import ConfigParser
import pickle

import tablib
import datetime
import dateutil.parser

import logging
import StringIO

import logging.handlers

import time



s=str(time.time())

LOG_FILENAME = 'tmp/log.%s.out' % s

# Set up a specific logger with our desired output level

my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=200000, backupCount=50)

my_logger.addHandler(handler)

log = logging.getLogger(__name__)




config = ConfigParser.ConfigParser()
config.read([os.path.expanduser('~/.pymotw')])
key = config.get('youtube', 'apikey')

api = gdata.youtube.service.YouTubeService(
        client_id='myid',
        developer_key=key)






TODAY="2012-01-09T08:15:05.000Z"


def get_feed(thing=None,feed_type=api.GetYouTubeUserFeed):

    if feed_type == 'user':
        feed = api.GetYouTubeUserFeed(username=thing)

    if feed_type == 'related':
        feed = api.GetYouTubeRelatedFeed(video_id=thing)

    if feed_type == 'comments':
        feed = api.GetYouTubeVideoCommentFeed(video_id=thing)

    feeds = []

    entries = []
    while feed:
        feeds.append(feed)
        feed = api.GetNext(feed)

    [entries.extend(f.entry) for f in feeds]

    return entries

#class Video(object):
#    pass
#
#class OBJ(object):
#    pass

def get_stats(entry):

    v=Video()
    v.id = entry.id.text.split('/')[-1]

    thedate = dateutil.parser.parse(entry.published.text)

    #v.published = entry.published.text
    v.date = thedate.strftime("%F")
    v.ago = (dateutil.parser.parse(TODAY)-thedate).days

    try:
        v.view_count = entry.statistics.view_count
        v.fav_count = entry.statistics.favorite_count
    except:
        v.fav_count = 0
        v.view_count = 0

    try:
        v.num_raters = entry.rating.num_raters
        v.rating = entry.rating.average
    except:
        v.num_raters = 0
        v.rating = 0

    try:
        v.comment_count = int(entry.comments.feed_link[0].count_hint)
    except:
        v.comment_count = 0

    v.title = entry.title.text
    v.content = entry.content.text
    v.tags = [c.term for c in entry.category[1:]]

    return v.__dict__



def myget(url,service=None):

    def myconverter(x):
        logfile=url.replace('/',':')+'.log'
        logfile=logfile[len('http://gdata.youtube.com/feeds/api/'):]
        if service:
            service2=service
        else:
            service2="None"

        my_logger.info("myget: %s\t%s" % (url, service2))
#        print url
        try:
            o = open('logs/%s' % logfile, 'w')
            o.write(x)
            o.close()
        except Exception,e:
            sys.stderr.write("ERROR: %r", e)
            pass

        if service == 'user_feed':
            return gdata.youtube.YouTubeUserFeedFromString(x)

        if service == 'comment_feed':
            return gdata.youtube.YouTubeVideoCommentFeedFromString(x)

        if service == 'comment_entry':
            return gdata.youtube.YouTubeVideoCommentEntryFromString(x)

        if service == 'video_feed':
            return gdata.youtube.YouTubeVideoFeedFromString(x)

        if service == 'video_entry':
            return gdata.youtube.YouTubeVideoEntryFromString(x)


    return api.GetWithRetries(url,
            converter=myconverter,
            num_retries=5,
            delay=4,
            backoff=5,
            logger=my_logger
            )


mapper={}
mapper[api.GetYouTubeUserFeed]='user_feed'
mapper[api.GetYouTubeVideoFeed]='video_feed'
mapper[api.GetYouTubeVideoCommentFeed]='comment_feed'



def getall(url, apiget=api.Get, max_results=100000):

    entries = []
    feeds = []

    if '?' in url:
        url = '%s&max-results=50' % url
    else:
        url = '%s?max-results=50' % url



    feed = myget(url,mapper[apiget])
    count = 0
    while (feed):

        if feed.entry:
            for e in feed.entry:
                count += 1
                if count > max_results:
                    break
                yield e

        if count >= max_results:
            print "breaking because %d > %d" %(count, max_results)
            break


        if feed.GetNextLink():
            feed = myget(feed.GetNextLink().href, mapper[apiget])
        else:
            feed = None


#def get_comments(entry,maxnum=100):
#    try:
#        coms,feeds = getall(entry.comments.feed_link[0].href,
#                            apiget=api.GetYouTubeVideoCommentFeed,
#                            maxnum=maxnum)
#        return coms,feeds
#    except:
#        return [],[]



def get_comments(entry, max_results=100):
    try:
        if entry.comments:
            comment_link = entry.comments.feed_link[0].href
            comment_generator = getall(comment_link, apiget=api.GetYouTubeVideoCommentFeed, max_results=max_results)
            for c in comment_generator:
                yield c
    except Exception, e:
        print str(e)
#        from IPython.ipapi import make_session; make_session()
#        from IPython.Debugger import Pdb; Pdb().set_trace()


def get_related_videos(entry, max_results=100):
    try:
        video_id = entry.id.text.split('/')[-1]
        url = "http://gdata.youtube.com/feeds/api/videos/%s/related" % video_id
        entry_generator = getall(url, apiget=api.GetYouTubeVideoFeed, max_results=max_results)
        for e in entry_generator:
            yield e
    except Exception, e:
        print str(e)
        raise


def get_response_videos(entry, max_results=100):
    try:
        video_id = entry.id.text.split('/')[-1]
        url = "http://gdata.youtube.com/feeds/api/videos/%s/responses" % video_id
        entry_generator = getall(url, apiget=api.GetYouTubeVideoFeed, max_results=max_results)
        for e in entry_generator:
            yield e
    except Exception, e:
        print str(e)
        raise



def getVideos(query=None,username=None, max_results=10000):
    url='http://gdata.youtube.com/feeds/api/users/%s/uploads' % username
    return getall(url, apiget=api.GetYouTubeVideoFeed,max_results=max_results)




def vintage(username, max_vids=10000, max_comments=10000):
    url='http://gdata.youtube.com/feeds/api/users/%s/uploads' % username

    entry_generator = getall(url, apiget=api.GetYouTubeVideoFeed, max_results=max_vids)

    idx = 0
    for e in entry_generator:
        idx += 1
        idtext = e.id.text.split('/')[-1]
        print "\n\nENTRY %03d: %s\n\n" % (idx,idtext)

#        if e.comments:
#            comment_link = e.comments.feed_link[0].href
#            print idtext, comment_link
#        else:
#            print idtext

        cdx = 0
        for c in get_comments(e, max_results=max_comments):
            cdx += 1
            cidtext = ':'.join(c.id.text.split('/')[-3:])
            print "%03d:%03d" % (idx,cdx), idtext, c.published.text, cidtext, c.author[0].name.text

            yield c

            #print idtext, dateutil.parser.parse(c.published.text).strftime("%FT%H:%M:%S"), c.author[0].name.text
#            time.sleep(.05)





vintages = []
if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        v = vintage(arg)
        #vintages.append(vintage(arg))


