import aiohttp
import discord
from discord.ext import tasks

from tokens import BEARER_TOKEN, DISCORD_TOKEN
from users import USERS

POLLING_RATE = 1

client = discord.Client()


@tasks.loop(seconds=10)  # repeat after every 10 seconds
async def main_loop(tweets_posted, channel):
    await check_tweets(tweets_posted, channel)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    tweets_posted = []
    channel = client.get_channel(id=631474839475060738)
    async for message in channel.history(limit=20):
        if message.author == client.user:
            text = message.content
            if 'twitter' in text and 'status' in text:
                tweets_posted.append(text.split('status/')[-1])
    main_loop.start(tweets_posted, channel)


async def send(message):
    channel = client.get_channel(id=631474839475060738)
    await channel.send(message)


async def check_tweets(tweets_posted, channel):
    headers = {'Authorization': f"Bearer {BEARER_TOKEN}"}
    vtuber_id = USERS['ksononair']
    translator_id = USERS['KamishiroTaishi']
    vtuber_url = f"https://api.twitter.com/2/users/{vtuber_id}/tweets?expansions=author_id,entities.mentions.username,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id&tweet.fields=author_id,conversation_id,created_at,in_reply_to_user_id,referenced_tweets,text&user.fields=id,url,name,username&max_results=10"
    translator_url = f"https://api.twitter.com/2/users/{translator_id}/tweets?expansions=author_id,entities.mentions.username,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id&tweet.fields=author_id,conversation_id,created_at,in_reply_to_user_id,referenced_tweets,text&user.fields=id,url,name,username&max_results=50"
    async with aiohttp.ClientSession() as session:
        async with session.get(vtuber_url, headers=headers) as responce:
            print(responce.status)
            result = await responce.json()
            buffer = []
            for tweet in result['data']:
                if tweet['id'] in tweets_posted:
                    print(tweet['id'], 'This vtuber\'s tweet already have been posted')
                    continue
                buffer.insert(0, tweet['id'])
            print(buffer)
            for idx in buffer:
                await send(f'https://twitter.com/ksononair/status/{idx}')
                tweets_posted.append(idx)

        async with session.get(translator_url, headers=headers) as responce:
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
