import requests
import textwrap
import shutil
import math
from time import sleep
from os.path import exists
from xml.etree import ElementTree

sleep_time           = 10
successful_responses = 0

user_name            = input("Enter your BGG UserName: ")
card_flag            = input("Card Mode? : (y/N)")
card_mode            = card_flag.lower() == "y" or card_flag.lower() == "yes"

######### Begin Functions ######### 

def get_value(item):
    return item.attrib['value']

def get_value_in_list(item, i):
    if(len(item) <= i):
        return ""
    else:
        return item[i].attrib['value']

def get_prop_text(elem, name):
    elem = elem.find(name)
    if elem is not None:
        return elem.text

def get_prop_value(elem, name):
    elem = elem.find(name)
    if elem is not None:
        return get_value(elem)

def get_links(elem, name):
    values = []
    elem = elem.findall('link')
    for item in elem:
        if (item.attrib['type'] == name):
            if item is not None:
                values.append(item)
    return values

def template_to_output_entry(game_info, card_mode):
    #Read the template.
    if(card_mode):
        with open('template_card.html', 'r') as file:
            template = file.read()
    else:    
        with open('template.html', 'r') as file:
            template = file.read()

    #Replace values in the template.
    template = template.replace('{{image}}', "./Images/" + game_info.obj_id + ".jpg" or "")
    template = template.replace('{{GameName}}', game_info.name or "")
    template = template.replace('{{Description}}', game_info.description or "")
    template = template.replace('{{Published}}', game_info.published or "")
    template = template.replace('{{Publisher}}', game_info.publisher or "")
    template = template.replace('{{Designer}}', game_info.designer or "")
    template = template.replace('{{Artist}}', game_info.artist1 or "")
    template = template.replace('{{Category}}', game_info.category1 + "<br/>" + game_info.category2)

    #Length of mechanics list
    mechanics_list_max_length = 75

    #Lengths of mechanics when placed together into a list.
    three_mechanics_length= len(game_info.mechanic1 + game_info.mechanic2 + game_info.mechanic3)
    four_mechanics_length = len(game_info.mechanic1 + game_info.mechanic2 + game_info.mechanic3 + game_info.mechanic4)

    if(len(game_info.mechanic1) > 0):
        template = template.replace('{{Cat0}}', game_info.mechanic1)
    else:
        template = template.replace('{{Cat0}}', "")
    if(len(game_info.mechanic2) > 0):
        template = template.replace('{{Cat1}}', " , " + game_info.mechanic2)
    else:
        template = template.replace('{{Cat1}}', "")
    if(len(game_info.mechanic3) > 0 and mechanics_list_max_length >= three_mechanics_length):
        template = template.replace('{{Cat2}}', " , " + game_info.mechanic3)
    else:
        template = template.replace('{{Cat2}}', "")
    if(len(game_info.mechanic4) > 0 and mechanics_list_max_length >= four_mechanics_length):
        template = template.replace('{{Cat3}}', " , " + game_info.mechanic4)
    else:
        template = template.replace('{{Cat3}}', "")
    
    template = template.replace('{{p}}', game_info.minplayers + " - " + game_info.maxplayers)         
    
    #If there is a range
    if(int(game_info.mintime) < int(game_info.maxtime)):
        template = template.replace('{{d}}', str(game_info.mintime) + " - " + str(game_info.maxtime))
    #Single game length
    else:
        template = template.replace('{{d}}', str(game_info.mintime))

    template = template.replace('{{Weight}}', str(round(float(game_info.avg_weight) * 2, 1) ))

    if("N/A" in game_info.my_rating):
        template = template.replace('{{Rating}}', str(round(float(game_info.avg_rating), 1)))
    else:
        template = template.replace('{{Rating}}', str(round((float(game_info.avg_rating) + float(game_info.my_rating)) / 2, 1)))

    with open('output.html', 'a') as file:
        file.write(template)

class GameInfo:
    def __init__(self, items, card_mode, obj_id, my_rating, avg_rating):

        if(card_mode):
            self.description = textwrap.shorten(get_prop_text(items[0], 'description') or "", width=500, placeholder='...')
        else:
            self.description = textwrap.shorten(get_prop_text(items[0], 'description') or "", width=1100, placeholder='...')

        self.image        = get_prop_text(items[0], 'image')
        self.name         = get_prop_value(items[0], 'name')
        self.obj_id       = obj_id
        self.my_rating    = my_rating
        self.avg_rating   = avg_rating
        self.minplayers   = str(get_prop_value(items[0], 'minplayers') or '')
        self.maxplayers   = str(get_prop_value(items[0], 'maxplayers') or '')
        self.published    = get_prop_value(items[0], 'yearpublished')
        self.publisher    = get_value_in_list(get_links(items[0], 'boardgamepublisher'), 0)
        self.designer     = get_value_in_list(get_links(items[0], 'boardgamedesigner'), 0)
        self.artist1      = get_value_in_list(get_links(items[0], 'boardgameartist'), 0)
        self.artist2      = get_value_in_list(get_links(items[0], 'boardgameartist'), 1)
        self.category1    = get_value_in_list(get_links(items[0], 'boardgamecategory'), 0)
        self.category2    = get_value_in_list(get_links(items[0], 'boardgamecategory'), 1)
        self.mechanic1    = get_value_in_list(get_links(items[0], 'boardgamemechanic'), 0)
        self.mechanic2    = get_value_in_list(get_links(items[0], 'boardgamemechanic'), 1)
        self.mechanic3    = get_value_in_list(get_links(items[0], 'boardgamemechanic'), 2)
        self.mechanic4    = get_value_in_list(get_links(items[0], 'boardgamemechanic'), 3)
        self.mintime  = str(get_prop_value(items[0], 'minplaytime') or '')
        self.maxtime  = str(get_prop_value(items[0], 'maxplaytime') or '')
        self.avg_weight = items[0].find('statistics').find('ratings').find('averageweight').attrib['value']

def download_image(obj_id):
    #If we have a local cache of the image, then don't try to redownload it, use the local copy.
    if(exists('./Images/' + obj_id + ".jpg") == False):
        #Download the image to the local cache.
        res = requests.get(game_info.image, stream = True)
        if res.status_code == 200:
            with open('./Images/' + obj_id + ".jpg", 'wb') as f:
                shutil.copyfileobj(res.raw, f)

######### End Functions ######### 

#Write the html header and link to the approprate CSS file.
if(card_mode):
    with open('output.html', 'w') as file:
            file.write('<html><head><link href="style_card.css" rel="stylesheet" type="text/css"></head><body>')
else:
    with open('output.html', 'w') as file:
            file.write('<html><head><link href="style.css" rel="stylesheet" type="text/css"></head><body>')

#Check if collection.xml exists. If it does, read it.
if(exists('collection.xml')):
    with open('collection.xml', 'r') as file:
        ur = file.read()
        items = ElementTree.fromstring(ur)

#Otherwise we request the XML from BGG
else:
    ur = requests.get("https://boardgamegeek.com/xmlapi2/collection?username=" + user_name + "&stats=1")
    with open('collection.xml', 'w') as file:
        file.write(ur.text.encode('utf-8'))
        items = ElementTree.fromstring(ur.content)

#Parsing user collection XML
for item in items:
    #Object id is needed to look up specific game information.
    obj_id     = item.attrib['objectid']

    #The name is grabbed here only for output to the console.
    name       = item.find('name').text

    #XML location for the game xml to be written.
    game_xml   = './game_xml/' + obj_id + '.xml'

    #Own status of the game, we only grab games that we own.
    own        = item.find('status').attrib['own'] == "1"

    #Ratings.
    my_rating  = item.find('stats').find('rating').attrib['value']
    avg_rating = item.find('stats').find('rating').find('average').attrib['value']

    #If we own the game, read it from the collection XML.
    if(own):

        #Check to see if the XML already exists. If it does, don't re-request it.
        if(exists(game_xml)):
            with open(game_xml, 'r') as file:
                gr = file.read()
                items = ElementTree.fromstring(gr)
        else:
            #This is a variable only use for error checking.
            return_text = "<error>"

            #While <error> is in the reponse, keep trying, but with a delay.
            while("<error>" in return_text):
                sleep(.5)

                #Grab the game info XML
                gr = requests.get("https://boardgamegeek.com/xmlapi2/thing?id=" + obj_id + "&stats=1")
                return_text = gr.text

                #This is all code related to delaying attempts when we get a timeout.
                if("<error>" in return_text):
                    error = ElementTree.fromstring(return_text)
                    print("Sleeping " + str(sleep_time) + " Seconds: " + error.find('message').text)
                    sleep(sleep_time)
                    sleep_time *= 2
                    successful_responses = 0
                else:
                    successful_responses += 1
                    if(successful_responses > 15):
                        sleep_time /= 2
                        sleep_time = max(10,sleep_time)

            #Write out the game info XML.
            with open(game_xml, 'w') as file:
                print("Writing: " + name + " to " + game_xml)
                file.write(gr.text.encode('utf-8'))
                items = ElementTree.fromstring(gr.content)

        #Now that we have all of the information we need, create the HTML page.
        if(items[0].attrib['type'] == "boardgame"):

            #Grab game information from xml file.
            game_info = GameInfo(items, card_mode, obj_id, my_rating, avg_rating)

            #Download the image if we don't have it.
            download_image(game_info.obj_id)        

            #Write to output using the approprate template.    
            template_to_output_entry(game_info,card_mode)

#Write the html trailer.
with open('output.html', 'a') as file:
        file.write("</body></html>")















