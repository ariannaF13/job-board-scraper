"""
Job finder
Author: Arianna Ford
5/22/2026
"""


"""
Legality checks: As long as sight does not:
    -require login
    -require a paywall
    -run anti robot cheks I'm avoiding
    -running curl -I "website-link-here" in cmd DOES NOT return an error code, then it can be used. 

Most risky sites to scrape:
    -LinkedIn
    -Indeed
    -Government Job Portals

CANNOT SHARE PERSONAL DATA OF RECRUITERS. Only share the job title, pay,, employer, location and link to the original website

Add disclaimer stating: 
"I aggregate publicly available job listings. 
All trademarks belong to their owners.
Users should verify listings on the original site."

CHECK TERMS OF SERVICE REGULARLY TO MAKE SURE I'M NOT VIOLATING ANYTHING. Possible create a regex search for this?????
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
#from flask import Flask, render_template, request
import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()

"""
Plan to implement scraping of the following places:
-Federal job listings
-State job listings: "https://www.governmentjobs.com/careers/wv?category[0]=IT%20and%20Computers&sort=PositionTitle%7CAscending"

Need to find more individual companies near us that may have job listings
    -TC Energy
    -Village Care Giving

Maybe have a section for non local companies too (later)
    -IBM

"""

#PARSERS ARE BELOW

def state_job_parser():
    #Uses requests to retrieve website and beautiful soup to pull content and organize
    url = "https://www.governmentjobs.com/careers/home/index?agency=wv&sort=PositionTitle&isDescendingSort=false&category=IT%20and%20Computers"
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.governmentjobs.com/careers/wv",
    }
    source = requests.get(url, headers=headers)
    soup = BeautifulSoup(source.content, 'html.parser')
    jobs = soup.find_all('li', class_='list-item')

    #State site lists several jobs, breaking down into useable text below using functions (clean_html, extract_pay) made lower in code
    for job in jobs:
        jobtitle = job.find('a', class_='item-details-link').get_text()
        information = job.find('ul', class_='list-meta')
        information_results = list(information.descendants)
        company = information_results[13]
        location = information_results[1]
        pay = information_results[4]
        part_url = job.find('a', class_='item-details-link')['href']
        jobtitle = clean_html(jobtitle)
        company = clean_html(jobtitle)
        location = clean_html(jobtitle)
        pay = extract_pay(pay)
        return_url = "https://www.governmentjobs.com" + part_url
        if company == "TEMPORARY EMPLOYMENT OPPORTUNTIES":
            company = "Division of Personnel"

        #save_job function saves all cleaned and organized data into database
        save_job(jobtitle, company, location, return_url, "https://www.governmentjobs.com/careers/wv", pay)



def tc_energy_job_parser():
    #Uses requests to retrieve website and beautiful soup to pull content and organize
    #TC Energy uses pagination and needs multiple pages scraped and cleaned before data can be stored
    base = "https://tcenergy.wd3.myworkdayjobs.com"
    start_url = base + "/en-US/CAREER_SITE_TC?locations=69babe4ce6380100bf72790e540e0000"

    #Site requires browser session (likely due to JavaScript-rendered content or dynamic loading), so Selenium WebDriver is used to load the page. 
    driver = webdriver.Chrome()
    driver.get(start_url)
    time.sleep(4)
    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        title_tags = soup.find_all("a", {"data-automation-id": "jobTitle"})
        titles = [t.text.strip() for t in title_tags]
        links_local = [base + t["href"] for t in title_tags]

        location_tags = soup.find_all("div", {"data-automation-id": "locations"})
        locs = []
        for tag in location_tags:
            raw = tag.text.strip()
            # Remove the Workday prefix
            cleaned = raw.replace("locations", "").strip()
            # Skip multi-location listings like "3 Locations"
            if cleaned[0].isdigit() and "Locations" in cleaned:
                locs.append("Multiple Locations")
                continue
            locs.append(cleaned)

        for i in range(len(titles)):
            jobtitle = clean_html(titles[i])
            location = clean_html(locs[i] if i < len(locs) else "")
            save_job(jobtitle, "TC Energy", location, links_local[i], start_url, "none listed")

        # Pagination
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='next']")
            if not next_button.is_enabled():
                break
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(4)
        except Exception:
            break
    driver.quit()




def clean_html(text):
    if pd.isna(text):
        return ""
    # Remove HTML tags
    text = BeautifulSoup(str(text), "html.parser").get_text(" ", strip=True)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_pay(text):
    if pd.isna(text):
        return ""
    text = BeautifulSoup(str(text), "html.parser").get_text(" ", strip=True)
    # Find dollar amounts or "Depends on Qualifications"
    match = re.search(r"\$\s*\d[\d,]*", text)
    if match:
        return match.group(0)
    return text



def df_runner():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("""
        SELECT title AS 'Job Title',
               company AS 'Company',
               location AS 'Location',
               pay AS 'Pay',
               url AS 'Link',
               source AS 'Source'
        FROM jobs
    """, conn)
    conn.close()
    return df

def save_job(title, company, location, url, source, pay):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")

    cursor.execute("""
        INSERT OR IGNORE INTO jobs (title, company, location, url, source, pay)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, company, location, url, source, pay))

    conn.commit()
    conn.close()




def database_refresh():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    before_count = cursor.fetchone()[0]
    cursor.execute("DELETE FROM jobs")
    conn.commit()
    conn.close()


    state_job_parser()
    tc_energy_job_parser()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    after_count = cursor.fetchone()[0]
    difference = after_count - before_count
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM refresh_stats")  # keep only latest
    cursor.execute("INSERT INTO refresh_stats (difference) VALUES (?)", (difference,))

    conn.commit()
    conn.close()
    





def send_all_emails():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM subscribers WHERE subscribed = 1")
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        email = row[0]
        send_individual_email(email)



def send_individual_email(email):
    df = df_runner()

    html_table = df.to_html(classes='table table-striped')
    #sender_email = "ari.fodre1219@gmail.com"
    sender_email = os.getenv("EMAIL_ADDRESS")
    #sender_password = "mzty jtgg krkr ylzt"
    sender_password = os.getenv("EMAIL_PASSWORD")
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = "Current job listings"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT difference FROM refresh_stats LIMIT 1")
    row = cursor.fetchone()
    difference = row[0] if row else 0
    conn.close()

    change_text = (
        f"{difference} new job(s) were added since the last refresh."
        if difference > 0 else
        "No new jobs were added since the last refresh."
    )
    # HTML body with table
    html_body = f"""
    <html>
    <body>
        <h2>Results</h2>
        <p>{change_text}</p>
        {html_table}
    </body>
    </html>
    """

    part = MIMEText(html_body, 'html')
    msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        print(f" Login failed! Check your username/App Password and security settings.")
        print(f"Server response: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'server' in locals():
            server.quit()
