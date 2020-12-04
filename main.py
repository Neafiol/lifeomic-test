import time
from typing import List, Tuple
import grequests

from bs4 import BeautifulSoup
from selenium import webdriver
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36"
DEPTH = 2
THREADS = 20


def get_urls(soup: BeautifulSoup) -> List[str]:
    """

    :param soup: page as bs
    :return: all urls in <a> and POST form
    """
    urls = [a["href"] if "http" in a["href"] else "https://lifeomic.com" + a["href"]
            for a in soup.find_all("a", {"href": True}) if "/" in a["href"]]

    urls += [a["action"] if "http" in a["action"] else "https://lifeomic.com" + a["action"]
             for a in soup.find_all("form", {"metod": "post"}) if "/" in a["action"]]

    return urls


def craul_pages(urls: List[str]) -> Tuple[List[str], List[str]]:
    """
    Craul page
    :param urls: list of pages for check
    :return: (all pages, pages with form)
    """
    page_with_forms = []
    res = []

    rs = [grequests.get(u, headers={
        "user-agent": USER_AGENT
    }) for u in set(urls)]

    for r in grequests.imap(rs, size=THREADS):
        assert len(r.text) > 1000, "request banned"
        print("complete", r.url, len(r.text))
        soup = BeautifulSoup(r.text, 'html5lib')
        res += get_urls(soup)
        if "formId" in r.text or soup.find("form", {"method": "POST"}):
            page_with_forms.append(r.url)

    return res, page_with_forms


def get_form_results(soup: BeautifulSoup, cookies: dict) -> List[Tuple[str, str]]:
    """
    Make post requests with random data in all forms on page
    :param soup: page as bs
    :param cookies:
    :return: list of (url, result)
    """

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
    urls, page_with_forms = craul_pages(["https://lifeomic.com"])
    all_urls = urls

    for _ in range(DEPTH):
        urls, forms = craul_pages(urls)
        all_urls_set = set(all_urls)
        urls = filter(lambda x: x not in all_urls_set, urls)
        all_urls += urls
        page_with_forms += forms

    print("Founded", len(set(all_urls)), "urls")
    with open("urls.txt", "w") as f:
        for u in set(all_urls):
            f.write(u + "\n")

    driver = webdriver.Firefox()
    form_responses = []
    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    print("Founded", len(set(page_with_forms)), "pages with forms")

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
