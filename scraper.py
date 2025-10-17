import requests
from bs4 import BeautifulSoup
import json
from flask import jsonify
def element_to_dict(element):
    """
    Recursively convert a BeautifulSoup element into a dictionary.
    Uses class names as keys if available, else tag name.
    """
    if element is None:
        return None

    data = {}

    for child in element.contents:
        if isinstance(child, str):
            text = child.strip()
            if text:
                return text
        elif child.name:
            key = child.get('class')[0] if child.get('class') else child.name
            value = element_to_dict(child)

            if key in data:
                if isinstance(data[key], list):
                    data[key].append(value)
                else:
                    data[key] = [data[key], value]
            else:
                data[key] = value

    if not data and element.get_text(strip=True):
        return element.get_text(strip=True)

    return data


def scrape_user_reviews_json(url):
    """
    Scrape the 'userReviews' section and convert it into a JSON-like dict.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    user_reviews_section = soup.find(attrs={"data-section": "userReviews"})
    if not user_reviews_section:
        return {}

    return element_to_dict(user_reviews_section)


def process(url):
    """
    Scrape all review pages for the given URL until duplicate reviews are found.
    """
    page = 1
    all_reviews = []
    seen_reviews = set()  # To track duplicates

    while True:
        page_url = url if page == 1 else f"{url}/{page}"
        print(f"Scraping: {page_url}")

        reviews_data = scrape_user_reviews_json(page_url)
        if not reviews_data:
            break

        review_list_container = reviews_data.get('MoreDropdown', {}).get("gsc-ta-active", {}).get("reviewList", {})
        if not isinstance(review_list_container, dict):
            break

        review_list = review_list_container.get('li', [])
        if not isinstance(review_list, list):
            review_list = [review_list]

        new_reviews_found = False

        for review in review_list:
            if not isinstance(review, dict):
                continue

            review_block = review.get("readReviewBox", {}).get("readReviewHolder", {})
            if not isinstance(review_block, dict):
                continue

            author_info = review_block.get("authorInfo", {})
            author_summary = author_info.get("authorSummary", {})

            author_name = author_summary.get("name") if isinstance(author_summary, dict) else None
            author_rating = None
            if isinstance(author_summary.get("span"), dict):
                author_rating = author_summary.get("span", {}).get("ratingStarNew")

            review_block["Author Information"] = {
                "Name": author_name,
                "Rating": author_rating
            }

            content_block = review_block.get("contentspace", {})
            if isinstance(content_block, dict):
                review_block["Content"] = {
                    "Review": content_block.get("contentheight", {}).get("div"),
                    "Title": content_block.get("title")
                }
            else:
                review_block["Content"] = {
                    "Review": content_block,
                    "Title": None
                }

            # Clean up old keys
            review.pop("readReviewBox", None)
            review_block.pop("authorInfo", None)
            review_block.pop("action", None)
            review_block.pop("contentspace", None)

            # Check for duplicates using a tuple of author + review text
            review_id = (author_name, review_block["Content"]["Review"])
            if review_id in seen_reviews:
                print("Duplicate review found. Stopping.")
                return json.dumps({"Title": reviews_data.get("h2"), "Review List": all_reviews}, indent=4)

            seen_reviews.add(review_id)
            all_reviews.append(review_block)
            new_reviews_found = True

        if not new_reviews_found:
            break

        page += 1

    return {"Title": reviews_data.get("h2"), "Review List": all_reviews}


def get_reviews(model,variant):
    review=process(f"https://www.cardekho.com/{model}/{variant}/user-reviews")
    return review
