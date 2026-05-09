import json
import os
import pathlib
from datetime import datetime

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed

API_URL = "https://tmmenumanagement.azurewebsites.net/api/WeekMenu/{location}"

LOCATION = os.getenv("LOCATION", "Geel")

WEBHOOK_URLS = [
    url.strip()
    for url in os.getenv("DISCORD_WEBHOOK_URLS", "").split(",")
    if url.strip()
]


class WeekMenu:
    def __init__(self, location):
        self.location = location

        self.data = self.fetch_data()

        self.items = self.data["items"]
        self.categories = self.data["categories"]

    def fetch_data(self):
        response = requests.get(
            API_URL.format(location=self.location),
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        parsed = json.loads(data)

        return parsed[0]

    def build_menu(self):
        """
        Final structure:

        {
          "Monday": {
            "Soep": {
              "nl": "Groentebouillon",
              "en": "Vegetable broth"
            }
          }
        }
        """

        menu = {}

        for category_id, days in self.items.items():

            category = self.categories[category_id]

            category_nl = category["NameNL"]

            for day, value in days.items():

                if day not in menu:
                    menu[day] = {}

                menu[day][category_nl] = {
                    "nl": value["ShortDescriptionNL"],
                    "en": value["ShortDescriptionEN"]
                }

        return menu

    def save_history(self, menu):
        now = datetime.now()

        year = now.strftime("%Y")
        week = now.strftime("%V")

        history_dir = pathlib.Path("history") / year

        history_dir.mkdir(parents=True, exist_ok=True)

        history_file = history_dir / f"week-{week}.json"

        with open(history_file, "w", encoding="utf-8") as file:
            json.dump(
                menu,
                file,
                indent=2,
                ensure_ascii=False
            )

        print(f"Saved history file: {history_file}")

    def send_discord(self, webhook_url, menu):

        webhook = DiscordWebhook(url=webhook_url)

        for day, categories in menu.items():

            embed = DiscordEmbed(
                title=day,
                color="03b2f8"
            )

            for category, translations in categories.items():

                dutch = translations["nl"]
                english = translations["en"]

                embed.add_embed_field(
                    name=category,
                    value=f"{dutch}\n\n*{english}*",
                    inline=False
                )

            webhook.add_embed(embed)

        response = webhook.execute()

        print(
            f"Webhook sent to {webhook_url[:50]}... "
            f"({response.status_code})"
        )


def main():

    if not WEBHOOK_URLS:
        raise Exception(
            "DISCORD_WEBHOOK_URLS environment variable is empty"
        )

    weekmenu = WeekMenu(LOCATION)

    menu = weekmenu.build_menu()

    weekmenu.save_history(menu)

    for webhook_url in WEBHOOK_URLS:
        weekmenu.send_discord(webhook_url, menu)


if __name__ == "__main__":
    main()