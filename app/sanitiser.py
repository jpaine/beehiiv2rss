from bs4 import BeautifulSoup


def sanitise_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "iframe", "form"]):
        tag.decompose()
    for tag in soup.find_all(attrs={"onclick": True}):
        del tag["onclick"]
    for tag in soup.find_all(attrs={"onload": True}):
        del tag["onload"]
    return str(soup)
