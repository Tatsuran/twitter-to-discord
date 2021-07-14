import aiohttp
import discord
from discord.ext import tasks

from tokens import BEARER_TOKEN, DISCORD_TOKEN

USERS = {
    'ksononair': '733990222787018753',
    'KamishiroTaishi': '1261539336278822912'
}
CHANNEL_ID = 631474839475060738
GUILD_ID = 631474839475060736
ROLE_ID = 669575938211708968
TL_TAG = '#組長TL'
LOOP_RATE_SEC = 5
DEEP_CHECK_AT = 1000
DISCORD_HISTORY_LIMIT = 50
TWITTER_HISTORY_DEEP = 50
TWITTER_HISTORY_NORMAL = 5

client = discord.Client()


# Main loop, repeats every xxx seconds
@tasks.loop(seconds=LOOP_RATE_SEC)
async def main_loop(tweets_posted, channel):
    await check_tweets(tweets_posted, channel, main_loop.current_loop)


# Action performed after bot is logged in and ready
@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    # Check channel history and grab id's of tweets that have already been posted
    tweets_posted = []
    channel = client.get_channel(id=CHANNEL_ID)
    # If limit=20 bot will check only last 20 messages in a channel from any user
    async for message in channel.history(limit=DISCORD_HISTORY_LIMIT):

        ## Ignore messages that are posted not from a bot account - OPTIONAL
        # if message.author != client.user:
        #     continue

        text = message.content
        # Ignore bot messages that does not contain tweet links
        if 'twitter' not in text or 'status' not in text:
            print('twitter or status not in', text)
            continue
        # Grab tweet id and add it to a list of ids
        for item in [row.split(' ')[1] for row in text.split('\n')]:
            if 'twitter' not in item or 'status' not in item:
                continue
            tweet_id = item.split('status/')[-1]
            tweets_posted.append(tweet_id)
    main_loop.start(tweets_posted, channel)


# Send message to a specific discord channel
async def send(message, channel_id):
    channel = client.get_channel(id=channel_id)
    await channel.send(message)


# Parameters for twitter requests, same parameters except max_results
def params(max_results=5):
    return {
        'tweet.fields': 'conversation_id,in_reply_to_user_id',
        'max_results': max_results
    }


# nothing-here-yet
async def check_tweets(tweets_posted, channel, loop_iteration):
    headers = {'Authorization': f"Bearer {BEARER_TOKEN}"}
    vtuber_id = USERS['ksononair']
    translator_id = USERS['KamishiroTaishi']
    vtuber_url = f'https://api.twitter.com/2/users/{vtuber_id}/tweets'
    translator_url = f'https://api.twitter.com/2/users/{translator_id}/tweets'
    parameters = params(TWITTER_HISTORY_NORMAL)
    role = client.get_guild(GUILD_ID).get_role(ROLE_ID)
    # At first launch and once in a while check more that 5 last tweets
    if loop_iteration % DEEP_CHECK_AT == 0:
        parameters = params(TWITTER_HISTORY_DEEP)

    async with aiohttp.ClientSession() as session:
        async with session.get(vtuber_url, headers=headers, params=parameters) as responce:
            print(responce.status)
            result = await responce.json()
            buffer = []
            for tweet in result['data']:
                # Prevent posting again tweets that are already in the channel
                if tweet['id'] in tweets_posted:
                    print(tweet['id'], 'This vtuber\'s tweet already have been posted')
                    continue
                # Place older tweets at the beginning (to be posted first)
                buffer.insert(0, tweet['id'])
            # Posting to discord
            for idx in buffer:
                await send(f'{role.mention} https://twitter.com/ksononair/status/{idx}', CHANNEL_ID)
                tweets_posted.append(idx)

        async with session.get(translator_url, headers=headers, params=parameters) as responce:
            print(responce.status)
            result = await responce.json()
            for tweet in result['data']:
                # Prevent posting again tweets that are already in the channel
                if tweet['id'] in tweets_posted:
                    print(tweet['id'], 'This translator\'s tweet already have been posted')
                    continue
                # Filter out tweets that are not replies
                if 'in_reply_to_user_id' not in tweet:
                    print(f'Not a reply, {tweet["id"]}')
                    continue
                # Filter out tweets that are not replies to a specific twitter id
                if tweet['in_reply_to_user_id'] != vtuber_id:
                    print(f'Wrong vtuber, {tweet["id"]}, {tweet["in_reply_to_user_id"]}')
                    continue
                # Filter our tweets that are not marked with a 'translation' tag
                if TL_TAG not in tweet['text']:
                    print(f'No {TL_TAG} tag, {tweet["id"]}, {tweet["in_reply_to_user_id"]}')
                    continue
                async for message in channel.history(limit=DISCORD_HISTORY_LIMIT):
                    # Don't edit messages that are not posted with this bot
                    if message.author != client.user:
                        continue
                    text = message.content
                    # Ignore messages that does not contain tweet url or if tweet id does not match
                    if 'twitter' not in text or 'status' not in text or tweet['conversation_id'] not in text:
                        continue
                    # Edit a message with vtuber tweet repost - att a translator tweet
                    new_content = message.content
                    new_content += f'\n{role.mention} https://twitter.com/KamishiroTaishi/status/{tweet["id"]}'
                    await message.edit(content=new_content)
                    tweets_posted.append(tweet['id'])


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
