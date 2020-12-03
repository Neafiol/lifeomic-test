import time

import grequests as grequests
import requests
from bs4 import BeautifulSoup
from requests_toolbelt.multipart.encoder import MultipartEncoder
from selenium import webdriver
from tqdm import tqdm as tqdm

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36"
DEPTH = 2
THREADS = 10


def get_urls(soup):
    urls = [a["href"] if "http" in a["href"] else "https://lifeomic.com" + a["href"]
            for a in soup.find_all("a", {"href": True}) if "/" in a["href"]]

    urls += [a["action"] if "http" in a["action"] else "https://lifeomic.com" + a["action"]
             for a in soup.find_all("form", {"metod": "post"}) if "/" in a["action"]]

    return urls


def parse_part(urls):
    page_with_forms = []
    res = []

    import grequests

    rs = [grequests.get(u, headers={
        "user-agent": USER_AGENT
    }) for u in set(urls)]

    for r in grequests.imap(rs, size=THREADS):
        print("complete", r.url)
        soup = BeautifulSoup(r.text, 'html5lib')
        res += get_urls(soup)
        if "formId" in r.text:
            page_with_forms.append(r.url)

    return res, page_with_forms


def get_form_results(soup, cookies):
    results = []
    for form in soup.find_all("form", {"method": "POST"}) + soup.find_all("d", {"method": "POST"}):
        furl = form["action"]

        data = {}
        for inpt in form.find_all("input", {"name": True}):

            val = inpt.attrs.get("value", "")
            if not val:
                val = "random text"
            data[inpt["name"]] = val

        mp_encoder = MultipartEncoder(fields=data)
        r = requests.post(furl,
                          data=mp_encoder,
                          headers={
                              "Content-Type": mp_encoder.content_type,
                              "user-agent": USER_AGENT
                          },
                          cookies=cookies
                          )
        results.append((furl, r.text))
        print(r.text)
    return results


if __name__ == "__main__":
    urls, page_with_forms = parse_part(["https://lifeomic.com"])
    all_urls = tasks = urls

    for i in range(DEPTH):
        urls, forms = parse_part(tasks)
        tasks = filter(lambda x: x not in all_urls, urls)
        all_urls += urls
        urls = tasks
        page_with_forms += forms

    print("Founded", len(set(all_urls)), "urls")
    with open("urls.txt", "w") as f:
        for u in set(all_urls):
            f.write(u + "\n")

    driver = webdriver.Firefox()
    form_responses = []
    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    print("Founded", len(set(page_with_forms)), "pages with forms")
    exit(0)
    for url in set(page_with_forms):
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html5lib')
        form_responses += get_form_results(soup, cookies)

    print("Getting results from", len(form_responses), "forms")
    with open("forms.txt", "w") as f:
        for form in form_responses:
            f.write(f"{len(form[1])}\n")

    driver.quit()
