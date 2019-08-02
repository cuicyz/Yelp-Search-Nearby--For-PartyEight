##Credit to scrapehero at Github(yelp_search.py)

from lxml import html
import unicodecsv as csv
import requests
from time import sleep
import re
import argparse
import json


def parse(url):
    headers = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chrome/70.0.3538.77 Safari/537.36'}
    success = False
    
    for _ in range(10):
        response = requests.get(url, verify=False, headers=headers)
        if response.status_code == 200:
            success = True
            break
        else:
            print("Response received: %s. Retrying : %s"%(response.status_code, url))
            success = False
    
    if success == False:
        print("Failed to process the URL: ", url)
    
    parser = html.fromstring(response.text)
    listing = parser.xpath("//li[@class='regular-search-result']")
    raw_json = parser.xpath("//script[contains(@data-hypernova-key,'yelp_main__SearchApp')]//text()")
    scraped_datas = []
    
    # Case 1: Getting data from new UI
    if raw_json:
        print('Grabbing data from new UI')
        cleaned_json = raw_json[0].replace('<!--', '').replace('-->', '').strip()
        json_loaded = json.loads(cleaned_json)
        search_results = json_loaded['searchPageProps']['searchResultsProps']['searchResults']
        
        for results in search_results:
            # Ad pages doesn't have this key.  
            result = results.get('searchResultBusiness')
            if result:
                is_ad = result.get('isAd')
                price_range = result.get('priceRange')
                position = result.get('ranking')
                name = result.get('name')
                ratings = result.get('rating')
                reviews = result.get('reviewCount')
                address = result.get('formattedAddress')
                phone = result.get('phone')
                neighborhood = result.get('neighborhoods')
                category_list = result.get('categories')
                full_address = address+' '+''.join(neighborhood)
                url = "https://www.yelp.com"+result.get('businessUrl')
                
                category = []
                for categories in category_list:
                    category.append(categories['title'])
                business_category = ','.join(category)

                # Filtering out ads
                if not(is_ad):
                    data = {
                        'business_name': name,
                        'rank': position,
                        'review_count': reviews,
                        'categories': business_category,
                        'rating': ratings,
                        'phone':phone,
                        'address': full_address,
                        'price_range': price_range,
                        'url': url
                    }
                    scraped_datas.append(data)
        return scraped_datas

    # Case 2: Getting data from OLD UI
    if listing:
        print('Grabbing data from OLD UI')

        for results in listing:    
            raw_position = results.xpath(".//span[@class='indexed-biz-name']/text()")
            raw_name = results.xpath(".//span[@class='indexed-biz-name']/a//text()")
            raw_ratings = results.xpath(".//div[contains(@class,'rating-large')]//@title")
            raw_review_count = results.xpath(".//span[contains(@class,'review-count')]//text()")
            raw_price_range = results.xpath(".//span[contains(@class,'price-range')]//text()")
            category_list = results.xpath(".//span[contains(@class,'category-str-list')]//a//text()")
            raw_address = results.xpath(".//address//text()")
            raw_phone=results.xpath(".//span[@class='biz-phone']//text()")
            is_reservation_available = results.xpath(".//span[contains(@class,'reservation')]")
            is_accept_pickup = results.xpath(".//span[contains(@class,'order')]")
            url = "https://www.yelp.com"+results.xpath(".//span[@class='indexed-biz-name']/a/@href")[0]

            name = ''.join(raw_name).strip()
            position = ''.join(raw_position).replace('.', '').strip()
            cleaned_reviews = ''.join(raw_review_count).strip()
            reviews =  re.sub("\D+", "", cleaned_reviews)
            categories = ','.join(category_list)
            phone=''.join(raw_phone).strip()
            cleaned_ratings = ''.join(raw_ratings).strip()
            if raw_ratings:
                ratings = re.findall("\d+[.,]?\d+", cleaned_ratings)[0]
            else:
                ratings = 0
            price_range = len(''.join(raw_price_range)) if raw_price_range else 0
            address  = ' '.join(' '.join(raw_address).split())
            reservation_available = True if is_reservation_available else False
            accept_pickup = True if is_accept_pickup else False
            data = {
                    'business_name': name,
                    'rank': position,
                    'review_count': reviews,
                    'categories': categories,
                    'phone':phones,
                    'rating': ratings,
                    'address': address,                    
                    'price_range': price_range,
                    'url': url
            }
            scraped_datas.append(data)
        return scraped_datas

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('place', help='Location/ Address/ zip code')
    search_query_help = """Available search queries are:\n
                            Restaurants,\n
                            Breakfast & Brunch,\n
                            Coffee & Tea,\n
                            Delivery,
                            Reservations"""
    argparser.add_argument('search_query', help=search_query_help)
    args = argparser.parse_args()
    place = args.place
    search_query = args.search_query

    result=[]
    for i in range(10):
        yelp_url = "https://www.yelp.com/search?find_desc=%s&find_loc=%s&start=%s" % (search_query,place,i*10)
        scraped_data = parse(yelp_url)
        result+=scraped_data
    with open("scraped_yelp_results_for_%s.csv" % (place), "wb") as fp:
        fieldnames = ['rank', 'business_name', 'review_count', 'categories', 'rating', 'address', 'price_range', 'url','phone']
        writer = csv.DictWriter(fp, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        if result:
            print ("Writing data to output file")  
            for data in result:
                writer.writerow(data)

