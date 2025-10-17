"""
Module defines the main entry point for the Car Review Scraper Actor.

This Actor fetches available car models and user reviews for specific models and variants
using structured scraping logic. The input defines what to fetch — either model info
or reviews for a given car model and variant.

Built using Apify SDK and BeautifulSoup for robust and scalable scraping.

Docs:
- Apify SDK: https://docs.apify.com/sdk/python
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc
"""

from __future__ import annotations
from apify import Actor
from bs4 import BeautifulSoup
from httpx import AsyncClient
import json
from .scraper import get_reviews  # assuming your scraper logic is modularized here


async def main() -> None:
    """Define the main entry point for the Apify Actor.

    Depending on the input parameters, this Actor either:
    1. Fetches available car models and variants.
    2. Retrieves user reviews for a given model and variant.

    The output is stored in the Apify dataset.
    """

    async with Actor:
        # Retrieve Actor input
        actor_input = await Actor.get_input() or {}
        mode = actor_input.get("mode", "models")  # 'models' or 'reviews'

        if mode == "models":
            # Fetch from local JSON file (car_info.json)
            try:
                Actor.log.info("Fetching car models and variants from local file...")
                with open("api/car_info.json", "r") as file:
                    data = json.load(file)

                await Actor.push_data({
                    "status": "success",
                    "data_type": "car_models",
                    "content": data
                })

            except Exception as e:
                Actor.log.error(f"Failed to load car models: {str(e)}")
                await Actor.push_data({"error": str(e)})

        elif mode == "reviews":
            model = actor_input.get("model")
            variant = actor_input.get("variant")

            if not model or not variant:
                msg = "Both 'model' and 'variant' are required for review fetching!"
                Actor.log.error(msg)
                await Actor.push_data({"error": msg})
                return

            try:
                Actor.log.info(f"Fetching user reviews for {model} ({variant})...")
                response = get_reviews(model, variant)

                # Ensure response is a dict, not a string
                if isinstance(response, str):
                    try:
                        response = json.loads(response)
                    except json.JSONDecodeError:
                        pass

                await Actor.push_data({
                    "status": "success",
                    "data_type": "reviews",
                    "model": model,
                    "variant": variant,
                    "content": response
                })

            except Exception as e:
                Actor.log.error(f"Error fetching reviews: {str(e)}")
                await Actor.push_data({"error": str(e)})

        else:
            Actor.log.warning(f"Unknown mode: {mode}")
            await Actor.push_data({"error": "Invalid mode. Use 'models' or 'reviews'."})
