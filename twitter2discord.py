import json

import aiohttp
import discord
from discord.ext import tasks

from tokens import BEARER_TOKEN, DISCORD_TOKEN

POLLING_RATE = 1
CHANNEL_ID = 631474839475060738
USERS = {
    'ksononair': '733990222787018753',
    'KamishiroTaishi': '1261539336278822912'
}

client = discord.Client()


# Main loop, repeats every xxx seconds
@tasks.loop(seconds=10)
async def main_loop(tweets_posted, channel):
    await check_tweets(tweets_posted, channel)


# Action performed after bot is logged in and ready
@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

    # Check channel history and grab id's of tweets that have already been posted
    tweets_posted = []
    channel = client.get_channel(id=CHANNEL_ID)
    async for message in channel.history(limit=20):
        # Ignore messages that are posted not from a bot account
        if message.author != client.user:
            continue
        text = message.content
        # Ignore bot messages that does not contain tweet links
        if 'twitter' not in text or 'status' not in text:
            continue
        # Grab tweet id and add it to a list of ids
        tweets_posted.append(text.split('status/')[-1])
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
async def check_tweets(tweets_posted, channel):
    headers = {'Authorization': f"Bearer {BEARER_TOKEN}"}
    vtuber_id = USERS['ksononair']
    translator_id = USERS['KamishiroTaishi']
    vtuber_url = f'https://api.twitter.com/2/users/{vtuber_id}/tweets'
    translator_url = f'https://api.twitter.com/2/users/{translator_id}/tweets'

    async with aiohttp.ClientSession() as session:
        async with session.get(vtuber_url, headers=headers, params=params(10)) as responce:
            print(responce.status)
            print(responce.request_info)
            result = await responce.json()
            print(json.dumps(result, indent=4, sort_keys=True))
            buffer = []
            for tweet in result['data']:
                if tweet['id'] in tweets_posted:
                    print(tweet['id'], 'This vtuber\'s tweet already have been posted')
                    continue
                buffer.insert(0, tweet['id'])
            print(buffer)
            for idx in buffer:
                await send(f'https://twitter.com/ksononair/status/{idx}', CHANNEL_ID)
                tweets_posted.append(idx)

        async with session.get(translator_url, headers=headers, params=params(50)) as responce:
            print(responce.status)
            result = await responce.json()
            for tweet in result['data']:
                if tweet['id'] in tweets_posted:
                    print(tweet['id'], 'This translator\'s tweet already have been posted')
                    continue
                if 'in_reply_to_user_id' not in tweet:
                    print(f'Not a reply, {tweet["id"]}')
                    continue
                if tweet['in_reply_to_user_id'] != vtuber_id:
                    print(f'Wrong vtuber, {tweet["id"]}, {tweet["in_reply_to_user_id"]}')
                    continue
                if '#組長TL' not in tweet['text']:
                    print(f'No #組長TL tag, {tweet["id"]}, {tweet["in_reply_to_user_id"]}')
                    continue
                async for message in channel.history(limit=20):
                    if message.author == client.user:
                        text = message.content
                        if 'twitter' in text and 'status' in text and tweet['conversation_id'] in text:
                            newcontent = message.content + f'\nhttps://twitter.com/KamishiroTaishi/status/{tweet["id"]}'
                            await message.edit(content=newcontent)
                            # await message.reply(f'https://twitter.com/KamishiroTaishi/status/{tweet["id"]}',
                            #                     mention_author=False)
                            tweets_posted.append(tweet['id'])


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
