#imports
import requests,json,discord,logging,asyncio,sys
from datetime import datetime

#load config
config = None
with open("config.json",'r') as config_file:
    config = json.load(config_file)
token = config["token"]
api_key = config["api_key"]

#hypixel skyblock api
uuid = 'a4907648-ada0-43ea-abcc-487a856b440e'
profile_id = '900b4bed-8a07-4f12-88b8-7b3022bc137c'
uuid_key = uuid.replace("-","")
profile_url = f"https://api.hypixel.net/v2/skyblock/profile?key={api_key}&uuid={uuid}&profile={profile_id}"

#discord
intents = discord.Intents.all()
client = discord.Client(intents=intents)
message: discord.Message = None
loop_running = False
channel_id = 1305841186514403421
my_id = 173015465638100993
mention_me = f"<@{my_id}>"
ping_message: discord.Message = None
already_pinged = False

#data
all_time_low_val = -1
all_time_low_str = ""
all_time_low_date = ""

#error handling
error_count = 0

#bot start
@client.event
async def on_ready():
    global loop_running

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="nach Cookie Preisen"))

    if not loop_running:
        client.loop.create_task(mainloop())
        loop_running = True

#reaction added
@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    global ping_message,already_pinged
    valid_reaction = False

    if ping_message is not None and reaction.message.id == ping_message.id: #message check
        if reaction.is_custom_emoji() and reaction.emoji.name == "booster_cookie" and reaction.emoji.id == 1305850403681730640: #reaction check
            valid_reaction = True
            if user.id == my_id:
                await ping_message.delete()
                ping_message = None
                already_pinged = False

    #remove if reaction invalid
    if not valid_reaction:
        await reaction.remove(user)

#main
async def mainloop():
    global message,already_pinged,ping_message,all_time_low_val,all_time_low_str,all_time_low_date
    while not client.is_closed():
        #cookie
        response = requests.get("https://api.hypixel.net/v2/skyblock/bazaar")
        try:
            data = response.json()
            last_updated_timestamp = data["lastUpdated"]
            booster_cookie = data["products"]["BOOSTER_COOKIE"]
            buy_price = booster_cookie["buy_summary"][0]["pricePerUnit"]
        except json.JSONDecodeError as e:
            await err(e)
            continue

        last_updated_date = datetime.fromtimestamp(last_updated_timestamp/1000)
        formatted_date = last_updated_date.strftime("%d.%m.%Y %H:%M:%S")

        formatted_buy = f"{buy_price:,.2f}"

        #bank
        response = requests.get(profile_url)
        try:
            data = response.json()
            if data["success"]:
                bank = data["profile"].get("banking",{}).get("balance",-1)
            else:
                bank = "ERR"
        except json.JSONDecodeError as e:
            await err(e)
            continue

        formatted_bank = f"{bank:,.2f}"

        final_string = f"{formatted_date}: {formatted_bank} / {formatted_buy}"

        #update all time low
        if all_time_low_val == -1 or all_time_low_val > buy_price:
            all_time_low_val = buy_price
            all_time_low_str = formatted_buy
            all_time_low_date = formatted_date

        #print in console
        print(final_string)

        #get channel
        channel: discord.TextChannel = client.get_channel(channel_id)

        #create embed
        embed = discord.Embed(
            title="Booster Cookie",
            description=formatted_buy,
            color=discord.Color.blue()
        )
        thumbnail = discord.File("./booster_cookie.png",filename="booster_cookie.png")
        embed.set_thumbnail(url="attachment://booster_cookie.png")
        embed.add_field(name="Bank",value=formatted_bank,inline=False)
        embed.add_field(name="All-Time-Low",value=f"{all_time_low_str}\n({all_time_low_date})")
        embed.set_footer(text=formatted_date)

        #send message
        if message != None:
            await message.edit(embed=embed)
        else:
            message = await channel.send(file=thumbnail,embed=embed)

        #ping if can buy
        if bank != -1 and buy_price <= bank and not already_pinged:
            ping_message = await channel.send(mention_me)
            emoji = discord.PartialEmoji(name="booster_cookie",id=1305850403681730640)
            await ping_message.add_reaction(emoji)
            already_pinged = True

        #wait
        await asyncio.sleep((error_count+1)*10)

async def err(e):
    global error_count
    error_count+=1
    print(f"Error catched, {error_count}/5: {e}")
    if error_count == 1:
        await client.get_channel(channel_id).send(f"{mention_me} help, look console!")
    elif error_count == 5:
        await client.close()

#run client
client.run(token=token,log_level=logging.WARN)