from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException, NoSuchElementException
import itertools
import json
import pandas as pd
from collections import OrderedDict
from bs4 import BeautifulSoup as bs
import random
import time
import datetime
from dateutil.parser import parse
import re
import os
import smtplib
from email.message import EmailMessage
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler('flightscrape.log')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

FILENAME = 'trips.json'


class Scraper:

    @staticmethod
    def _add_date_range(input_dict):
        """
        Accesses the departure date and return date from a dictionary.
        Considers an allowance of +- 1 day for both departure and return
        dates, then computes all possible valid combinations of date pairs.

        :param input_dict: dictionary containing trip info
        :returns: a list of tuples each containing two datetime objects
        (departure and return dates)
        """
        dep_date = parse(input_dict['Dep_date'], dayfirst=True).date()
        ret_date = parse(input_dict['Ret_date'], dayfirst=True).date()
        day = datetime.timedelta(days=1)
        dep_datelist = [dep_date - day, dep_date, dep_date + day]
        ret_datelist = [ret_date - day, ret_date, ret_date + day]
        datelist = []
        for pair in itertools.product(dep_datelist, ret_datelist):
            if pair[0] < pair[1]:
                datelist.append(pair)
        return datelist

    options = Options()
    options.headless = True
    with open(FILENAME) as f:
        user_dict = json.load(f)

    arbi_val = next(iter(user_dict.values()))[0]
    columns = ['Name'] + [k for k in arbi_val.keys()] + ['Date_pairs']
    rows = []
    for name, trips in user_dict.items():
        for trip in trips:
            # dunder func method is used because we cannot call a static
            # method inside class body (descriptor binding)
            date_pairs = _add_date_range.__func__(trip)
            row = [name] + list(trip.values()) + [date_pairs]
            rows.append(row)

    data = pd.DataFrame(rows, columns=columns)

    def __init__(self):
        self.data = Scraper.data
        self.driver = webdriver.Firefox(options=Scraper.options)
        logger.debug('Firefox webdriver initiated')

    def __str__(self):
        return type(self).__name__

    def scrape_site(self):
        """
        Main function used to scrape the website according to the list
        of URLs. Collects the information and converts it to a pandas
        DataFrame to be saved to a csv file.
        """
        frames = []
        for i in range(len(self.data)):
            urls = self.create_urls(i)
            logger.debug(f'url batch {i+1} created. Commencing scrape...')
            for j, url in enumerate(urls, 1):
                time.sleep(random.randint(1, 3))
                logger.debug(f'scraping url no. {j} from batch {i+1}')
                soup = self.scrape_page(url)
                results = self.parse_page(soup)
                logger.debug(f'parsed page for url no. {j} from batch {i+1}')
                results['Target Price(RM)'] = self.data.iloc[i]['Target_price']
                results['Email'] = self.data.iloc[i]['Email_address']
                df = pd.DataFrame(results)
                df.insert(0, column='Name', value=self.data.iloc[i, 0])
                df.insert(3, column='Departing Date',
                          value=self.data.iloc[i]['Date_pairs'][j - 1][0])
                df.insert(7, column='Returning Date',
                          value=self.data.iloc[i]['Date_pairs'][j - 1][1])
                frames.append(df)
                logger.debug(f'done processing url no. {j} from batch {i+1}')
        logger.debug('finished scraping, closing webdriver...')
        self.driver.quit()
        combined = pd.concat(frames, ignore_index=True)
        combined.to_csv(f'{str(self)}.csv')

    def scrape_page(self, url):
        """
        Sends a GET request to the URL being scraped and waits for the page
        to load completely before dumping the page source into a beautiful
        soup object.

        :param url: full url of the page to be scraped
        :returns: page source converted to a beautiful soup object
        """
        timeout = 50
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, timeout).until(self.elem_present)
            self.close_popup()
        except TimeoutException:
            print(f'Timed out waiting for {url} to load')

        if self.sort_cheap is not None:
            try:
                cheapest_tab = self.driver.find_element(By.XPATH,
                                                        self.sort_cheap)
                cheapest_tab.click()
                time.sleep(2)
            except NoSuchElementException:
                pass

        soup = bs(self.driver.page_source, 'lxml')
        return soup

    def parse_page(self, soup):
        """
        Parses the beautiful soup object to collect all the required
        information.

        :param soup: beautiful soup object to be parsed
        :returns: an OrderedDict with flight parameters as keys and lists of
        relevant information as values
        """
        all_flights = soup.select(self.all_flights_tag)[:4]
        data = OrderedDict()
        for flight in all_flights:
            if isinstance(self.airline_tag, str):
                airlines = flight.select(self.airline_tag)
                airlines = [x.text for x in airlines]
            else:
                airlines = flight.select(self.airline_tag[0])
                airlines = [x.get(self.airline_tag[1]) for x in airlines]
            dep_airline, ret_airline = airlines[0], airlines[1]
            data.setdefault('Departing Airline', []).append(dep_airline)
            data.setdefault('Returning Airline', []).append(ret_airline)

            times = flight.select(self.times_tag)
            times = [x.text.split('+')[0].strip() for x in times]
            dep_time_1, dep_time_2 = times[0], times[1]
            ret_time_1, ret_time_2 = times[2], times[3]

            durations = flight.select(self.duration_tag)
            durations = [x.text.strip() for x in durations]
            dep_duration, ret_duration = durations[0], durations[1]

            data.setdefault('Departing Time(Takeoff)', []).append(dep_time_1)
            data.setdefault('Departing Time(Arrival)', []).append(dep_time_2)
            data.setdefault('Dep. Flight Duration', []).append(dep_duration)
            data.setdefault('Returning Time(Takeoff)', []).append(ret_time_1)
            data.setdefault('Returning Time(Arrival)', []).append(ret_time_2)
            data.setdefault('Ret. Flight Duration', []).append(ret_duration)

            airports = flight.select(self.airports_tag)
            airports = [x.text for x in airports]
            airport_1, airport_2 = airports[0], airports[len(airports) // 2]
            data.setdefault('Source Airport', []).append(airport_1)
            data.setdefault('Destination Airport', []).append(airport_2)

        prices = soup.select(self.price_tag)[:4]
        prices = [re.search(r'\d+', x.text.strip()).group()
                  for x in prices]
        data['Price(RM)'] = prices

        return data


class Skyscanner(Scraper):

    def __init__(self):
        """
        Initialize the css selectors and extra details used to find the
        required information as instance attributes
        """
        super().__init__()
        self.elem_present = EC.presence_of_element_located((By.CSS_SELECTOR,
                                                            'div.day-list-progress'
                                                            + '[style="width: 100%; display: none;"]'))
        self.sort_cheap = '//td[@class="tab"][@data-tab="price"]'
        self.all_flights_tag = 'div.ItineraryContent__container-1Sb_S'
        self.airline_tag = ('img.AirlineLogo__big-logo-image-3V2-Z', 'title')
        self.times_tag = 'span.LegInfo__times-Qn_ji'
        self.duration_tag = 'span.LegInfo__duration-2VgVw'
        self.airports_tag = 'span.LegInfo__tooltipTarget-njlsT'
        self.price_tag = 'a.CTASection__price-2bc7h.price'
        self.dialogbox_tag = 'button.bpk-modal__close-button-2a-Xb '

    def create_urls(self, row_num):
        """
        Creates urls for scraping the skyscanner website using data from
        the 'data' DataFrame object associated with the Scraper superclass.

        :param row_num: Current row number of dataframe associated with
        the Scraper superclass
        :returns: a list of urls to scrape
        """
        row = self.data.iloc[row_num]
        urls = []
        for pair in row['Date_pairs']:
            url = ('https://www.skyscanner.com.my/transport/flights/'
                   + row['Origin'].lower() + '/'
                   + row['Destination'].lower() + '/'
                   + str(pair[0]) + '/'
                   + str(pair[1]) + '/'
                   + '?adults=1&children=0&adultsv2=1&childrenv2=&infants=0&cabinclass=economy&rtn=1'
                   + '&preferdirects=false&outboundaltsenabled=false&inboundaltsenabled=false&ref=home#results')
            urls.append(url)
        return(urls)

    def close_popup(self):
        """
        check for the presence of pop-up windows and closes them
        """
        try:
            close = self.driver.find_element(By.CSS_SELECTOR,
                                             self.dialogbox_tag)
            close.click()
        except NoSuchElementException:
            pass


class Kayak(Scraper):

    def __init__(self):
        """
        Initialize the css selectors and extra details used to find the
        required information as instance attributes
        """
        super().__init__()
        elem = 'div.Common-Results-ProgressBar.theme-dark.Hidden'
        self.elem_present = EC.presence_of_element_located((By.CSS_SELECTOR,
                                                            elem))
        self.sort_cheap = None
        self.all_flights_tag = 'div.mainInfo'
        self.airline_tag = 'div.section.times div.bottom'
        self.times_tag = 'span.time-pair'
        self.duration_tag = 'div.section.duration div.top'
        self.airports_tag = 'div.section.duration div.bottom span:not(.sep)'
        self.price_tag = 'div.multi-row.featured-provider span.price.option-text'
        self.dialogbox_tag = 'button.Button-No-Standard-Style.close'

    def create_urls(self, row_num):
        """
        Creates urls for scraping the Kayak website using data from the
        'data' DataFrame object associated with the Scraper superclass.

        :param row_num: Current row number of dataframe associated with
        the Scraper superclass
        :returns: a list of urls to scrape
        """
        row = self.data.iloc[row_num]
        urls = []
        for pair in row['Date_pairs']:
            url = ('https://www.kayak.com.my/flights/'
                   + f"{row['Origin']}-{row['Destination']}/"
                   + f"{pair[0]}/{pair[1]}"
                   + '?sort=price_a')
            urls.append(url)
        return(urls)

    def close_popup(self):
        """
        check for the presence of pop-up windows and closes them
        """
        popup_tag = 'input.Common-Widgets-Text-TextInput.driveByUserAddress'
        try:
            popup = self.driver.find_element(By.CSS_SELECTOR, popup_tag)
            close = self.driver.find_elements(By.CSS_SELECTOR,
                                              self.dialogbox_tag)
            try:
                close[-2].click()
            except ElementNotInteractableException:
                close[-1].click()
        except NoSuchElementException:
            pass

# class Googleflights(Scraper):

#     def __init__(self):
#         super().__init__()

#     def create_urls(self, row_num):
#         """
#         Creates urls for scraping Google Flights using data from the
#         'data' DataFrame object associated with the parent Scraper class.

#         :param self: Googleflights class instance
#         :param row_num: Current row number of dataframe associated with
#         the Scraper class
#         :returns: a list of urls
#         """
#         row = self.data.iloc[row_num]
#         urls = []
#         for pair in row['Date_pairs']:
#             url = ('https://www.google.com/flights?hl=en&gl=my#flt='
#                    + f"{row['Origin']}.{row['Destination']}.{str(pair[0])}"
#                    + f"*{row['Destination']}.{row['Origin']}.{str(pair[1])}"
#                    + ';c:MYR;e:1;sd:1;t:f')
#             urls.append(url)
#         return(urls)


spider = Skyscanner()
spider.scrape_site()
# urls = spider.create_urls(0)
# soup = spider.scrape_page(urls[0])
# contents = spider.parse_page(soup)
# spider.driver.quit()
# import pprint
# pprint.pprint(contents)
