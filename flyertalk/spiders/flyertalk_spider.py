import scrapy
import re
from flyertalk.processors import to_int
from flyertalk.items import PostItem, UserItem, ThreadItem
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import logging


class FlyertalkSpider(scrapy.Spider):
    name = 'flyertalk'
    patterns = {'thread_id': re.compile('\/(\d+)'),
                # Remove this below one.
    'next_page_url': "//*[@class='pagenav']//*[@href and contains(text(), '>')]/@href" }

    url = "https://www.flyertalk.com/forum/"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        domain = getattr(self, "domain", None)
        url = getattr(self, "url", None)
    
        self.allowed_domains = ["flyertalk.com"]
        self.start_urls = [self.url]

    def paginate(self, response, pattern, next_page_callback):
        """Returns a scrapy.Request for the next page, or returns None if no next page found.
        response should be the Response object of the current page."""
        # This gives you the href of the '>' button to go to the next page
        # There are two identical ones with the same XPath, so just extract_first.
        next_page = response.xpath(pattern)

        if next_page:
            url = response.urljoin(next_page.extract_first())
            logging.info("NEXT PAGE IS: %s" % url)
            return scrapy.Request(url, next_page_callback, errback=self.logError)
        else:
            logging.info("NO MORE PAGES FOUND")
            return None

    def parse(self, response):
        # Parse the board (aka index) for forum URLs
        forum_urls = response.xpath("//div[@class='mobileMenu']//a[starts-with(@href, '/forum') and not(contains(@href, '/members/'))]/@href").extract()
        
        for url in forum_urls:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_forum)

    def parse_forum(self, response):
        logging.info(f"STARTING NEW FORUM SCRAPE (GETTING THREADS) at {response.url}")
        thread_urls = response.xpath('.//div[starts-with(@id, "td_threadtitle")]/div/h4/a[not(parent::span)]/@href').extract()

        logging.debug(f"Thread URLs found: {thread_urls}");

        subforum_xpath_expression = f"//div[@class='trow-group']//a[starts-with(@href, '{self.url}') and not(contains(@href, '/members/'))]/@href"
        subforum_urls = response.xpath(subforum_xpath_expression).extract()

        logging.debug(f"Subforum URLs found: {subforum_urls}");
        
        for url in thread_urls:
             yield scrapy.Request(response.urljoin(url), callback=self.parse_posts, errback=self.logError)
             
        for url in subforum_urls:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_forum, errback=self.logError)

        # return the next forum page if it exists
        pattern = "//a[@rel='next' and normalize-space(text()) = '>']/@href"
        yield self.paginate(response, pattern=pattern, next_page_callback=self.parse_forum)
        
    def parse_posts(self, response):
        logging.info(f"STARTING NEW POSTS SCRAPE AT:{response.url}")

        thread = ThreadItem()
        try:
            thread['thread_id'] = to_int(re.findall(self.patterns['thread_id'], response.url)[0])
        
            thread['thread_name'] = response.xpath("normalize-space(//h1[@class='threadtitle'])").extract_first()

            yield thread
        except Exception as e:
            self.logger.warning("Failed to extract thread data for thread: %s - error:\n %s", response.url, str(e))
            return

        # Scrape all the posts on a page for post & user info
        for post in response.xpath("//div[contains(@class,'tpost')]"):
            p = PostItem()

            p['thread_id'] = thread['thread_id']
            try:
                p['timestamp'] = self.extractDate(post.get())
                extract = post.xpath(".//*[contains(@id,'post_message_')]")
                p['raw_message'] = ''.join(extract.xpath('./node()').extract())
                post_id_str = extract.xpath("@id").get()
                p['post_id'] = ''.join(filter(str.isdigit, post_id_str))
                p['user_name'] = post.xpath(".//a[@class='bigusername']/text() | .//a[@class='bigusername']//text()").get()
                p['post_no'] = post.xpath('.//div[@class="trow-group"]//a/strong/text()').extract_first()
                p['post_url'] = post.xpath('.//div[@class="tcell text-right"]//a/@href').extract_first()
               
                yield p

            except Exception as e:
                self.logger.warning("Failed to extract post for thread: %s - exception: %s, args: %s", response.url, type(e).__name__, str(e.args))
                if "div-gpt-ad" not in post.get():
                    self.logger.warning("Response %s html:\n %s", response.url, post.get())
                continue

            try:
                p['user_name'] = response.xpath("normalize-space(//a[@class='bigusername'])").extract_first()

            except Exception as e:
                self.logger.warning("Failed to extract username for thread: %s, post: %d - defaulting to -1", response.url, p['post_id'], e)
                p['user_name'] = "unknown"

        # Pagination across thread: search for the link that the next button '>' points to, if any

        pattern = "//div[@id='mb_pagenav']//a[@id='mb_pagenext' and @class='button primary hollow']/@href"
        yield self.paginate(response, pattern=pattern, next_page_callback=self.parse_posts)

    def logError(self, error):
        logging.error(error);
    
    def extractDate(self, post):
        pattern = r'<!-- status icon and date -->(.*?)<!-- \/ status icon and date -->'

        # Search for the pattern in the HTML content
        match = re.search(pattern, post, re.DOTALL)

        # Extract the text between the comments if a match is found
        if match:
            text_between_comments = match.group(1).strip()
            text_between_comments = re.sub('<[^>]+>', '', text_between_comments)  # Remove HTML tags
            date_str = text_between_comments.replace('\n', '').replace('\r', '').replace('\t', '')  # Remove newlines
            custom_date_mappings = {
                    'Yesterday': (datetime.now() - timedelta(days=1)).strftime('%b %d, %y'),
                    'Today': datetime.now().strftime('%b %d, %y'),
                }

                # Replace custom date strings with actual date strings
            for custom_date, actual_date in custom_date_mappings.items():
                    date_str = date_str.replace(custom_date, actual_date)

                # Parse the date string into a datetime object
            parsed_date = datetime.strptime(date_str, '%b %d, %y, %I:%M %p')

                # Convert the datetime object to ISO format
            iso_date_str = parsed_date.isoformat()
            return iso_date_str
