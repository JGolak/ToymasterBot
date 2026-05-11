import os
import asyncio
import subprocess
from playwright.async_api import async_playwright
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

# Ensure Firefox is installed at runtime (Railway fix)
subprocess.run(["playwright", "install", "--with-deps", "firefox"], check=False)

# Load environment variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
USER_ID = os.getenv("DISCORD_USER_ID")
PAGE_URL = os.getenv("FACEBOOK_PAGE_URL")

# Validate environment variables
if not TOKEN:
    print("❌ ERROR: DISCORD_BOT_TOKEN is missing")
if not USER_ID:
    print("❌ ERROR: DISCORD_USER_ID is missing")
if not PAGE_URL:
    print("❌ ERROR: FACEBOOK_PAGE_URL is missing")

USER_ID = int(USER_ID)

last_post = None

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def get_latest_post():
    print("🔍 Checking Facebook page...")

    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = await browser.new_page()
            await page.goto(PAGE_URL, timeout=60000)
            await page.wait_for_timeout(5000)

            selectors = [
                "div[data-ad-preview='message']",
                "div.x1iorvi4.x1pi30zi.x1l90r2v",
                "div[role='article']"
            ]

            for sel in selectors:
                posts = await page.query_selector_all(sel)
                if posts:
                    print(f"✅ Found posts using selector: {sel}")
                    text = await posts[0].inner_text()
                    await browser.close()
                    return text

            print("⚠️ No posts found with any selector")
            await browser.close()
            return None

    except Exception as e:
        print(f"❌ Facebook scraping error: {e}")
        return None



@tasks.loop(seconds=60)
async def check_page():
    global last_post

    latest = await get_latest_post()

    if latest is None:
        print("⚠️ No latest post detected")
        return

    if last_post is None:
        print("📌 Initial post stored")
        last_post = latest
        return

    if latest != last_post:
        print("🚨 NEW POST DETECTED!")
        user = await client.fetch_user(USER_ID)
        await user.send(f"📢 **New Toymaster Post Detected!**\n\n{latest}\n\n{PAGE_URL}")
        last_post = latest
    else:
        print("⏳ No new posts")


@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    print("🔁 Starting Facebook check loop...")
    check_page.start()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "!test":
        user = await client.fetch_user(USER_ID)
        await user.send("Test message from the bot — DM system works!")


client.run(TOKEN)
