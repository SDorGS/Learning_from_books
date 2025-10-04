import requests
import lxml.html

html = requests.get('https://store.steampowered.com/explore/new')
doc = lxml.html.fromstring(html.content)

new_releases = doc.xpath('//div[@id="tab_newreleases_content"]')[0]

titles = new_releases.xpath('.//div[@class = "tab_item_name"]/text()')
print(titles)
tags_divs = new_releases.xpath('.//div[@class = "tab_item_top_tags"]/text()')
tags = []	
prices = new_releases.xpath('.//div[@class = "discount_final_price"]/text()')
print(prices)
for div in tags_divs:
    tags.append(div.text_content())
platform_div= new_releases.xpath('.//div[@class = "tab_item_details"]')
total_platforms = []


for game in platform_div:
    temp = game.xpath('.//span[contains(@class, "platform_img")]')
    platforms= [t.get('class').split(' ')[-1] for t in temp]
    if 'hmd_separator' in platforms:
        platforms.remove('hmd_separator')
    total_platforms.append(platforms)

output = []
for info in zip(titles, prices, tags, total_platforms):
    resp = {}
    resp['title'] = info[0]
    resp['price'] = info[1]
    resp['tags'] = info[2]
    resp['platforms'] = info[3]
    output.append(resp)
