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

#notify
already_pinged = False
ping_dismissed = False

#data
bank = -1
bank_date = ""
all_time_low_val = -1
all_time_low_str = ""
all_time_low_date = ""
poll_bank_interval = 15

#error handling
error_count = 0
error_message: discord.Message = None

#bot start
@client.event
async def on_ready():
    global loop_running

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="nach Cookie Preisen"))

    if not loop_running:
        client.loop.create_task(mainloop())
        loop_running = True
    
    print(f"But running as {client.user}")

#reaction added
@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    global ping_message,already_pinged,error_message,error_count,ping_dismissed
    valid_reaction = False

    is_ping_message = (ping_message is not None and reaction.message.id == ping_message.id)
    is_error_message = (error_message is not None and reaction.message.id == error_message.id)

    if is_ping_message or is_error_message: #message check
        if reaction.is_custom_emoji() and reaction.emoji.name == "booster_cookie" and reaction.emoji.id == 1305850403681730640: #reaction check
            valid_reaction = True
            if user.id == my_id:
                if is_ping_message:
                    await ping_message.delete()
                    ping_message = None
                    already_pinged = False
                    ping_dismissed = True
                else:
                    await error_message.delete()
                    error_message = None
                    error_count = 0

    #remove if reaction invalid
    if not valid_reaction:
        await reaction.remove(user)

#other functions
def get_emoji() -> discord.PartialEmoji:
    return discord.PartialEmoji(name="booster_cookie",id=1305850403681730640)

def format_date(date: str):
    return date.strftime("%d.%m.%Y %H:%M:%S")

def format_float(val: float):
    return f"{val:,.2f}"

#main
async def mainloop():
    global message,already_pinged,ping_message,all_time_low_val,all_time_low_str,all_time_low_date,bank,bank_date,ping_dismissed,error_count
    poll_bank = 0
    while not client.is_closed():
        try:
            #cookie
            response = requests.get("https://api.hypixel.net/v2/skyblock/bazaar")
            response.raise_for_status()
            data = response.json()

            last_updated_timestamp = data["lastUpdated"]
            booster_cookie = data["products"]["BOOSTER_COOKIE"]
            buy_price = booster_cookie["buy_summary"][0]["pricePerUnit"]

            last_updated_date = datetime.fromtimestamp(last_updated_timestamp/1000)
            formatted_date = format_date(last_updated_date)

            formatted_buy = format_float(buy_price)

            #bank
            if poll_bank > 0:
                poll_bank-=1
            else:
                poll_bank = poll_bank_interval
                response = requests.get(profile_url)
                response.raise_for_status()
                data = response.json()

                if data["success"]:
                    bank = data["profile"].get("banking",{}).get("balance",-1)
                    ping_dismissed = False
                if bank >= 0:
                    bank_date = format_date(datetime.now())
                else:
                    formatted_bank = "No Data"
            formatted_bank = format_float(bank)

            #update all time low
            if all_time_low_val == -1 or all_time_low_val > buy_price:
                all_time_low_val = buy_price
                all_time_low_str = formatted_buy
                all_time_low_date = formatted_date

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
            embed.add_field(name="Bank",value=f"{formatted_bank}\n({bank_date})",inline=False)
            embed.add_field(name="All-Time-Low",value=f"{all_time_low_str}\n({all_time_low_date})")
            embed.set_footer(text=formatted_date)

            #send message
            if message != None:
                await message.edit(embed=embed)
            else:
                message = await channel.send(file=thumbnail,embed=embed)

            #ping if can buy
            if bank != -1 and buy_price <= bank and not already_pinged and not ping_dismissed:
                ping_message = await channel.send(f"{mention_me} You can buy!")
                emoji = get_emoji()
                await ping_message.add_reaction(emoji)
                already_pinged = True
            
            error_count-=1
        except (requests.RequestException, json.JSONDecodeError) as e:
            await err(e)
            continue

        #wait
        await asyncio.sleep((error_count+1)*20)

#error handling
async def err(e):
    global error_count,error_message
    error_count+=1
    print(f"Error catched, {error_count}/5: {e}")
    if error_count == 5:
        await client.get_channel(channel_id).send(f"{mention_me} too many errors. Shutting down!")
        await client.close()

#run client
client.run(token=token,log_level=logging.WARN)