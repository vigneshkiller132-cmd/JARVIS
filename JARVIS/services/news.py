import urllib.request
import xml.etree.ElementTree as ET
import config

def get_news():
    try:
        req = urllib.request.Request("https://news.google.com/rss", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            xml_data = r.read()
        root_xml = ET.fromstring(xml_data)
        items = root_xml.findall('./channel/item')
        if not items: return f"Could not find any news {config.YOUR_NAME}."
        headlines = [item.find('title').text for item in items[:4]]
        return f"Here are the top headlines {config.YOUR_NAME}: " + ". ".join(headlines) + "."
    except Exception:
        return f"Could not fetch the news {config.YOUR_NAME}."