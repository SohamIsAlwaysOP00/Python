import requests
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_otp(email):
    # This function would need to be implemented based on the actual OTP retrieval method used by Instagram
    pass

def create_instagram_account(otp):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.instagram.com/")
    
    # Fill out registration form
    driver.find_element_by_name("username").send_keys("du7sgdjdhn")
    driver.find_element_by_name("password").send_keys("opopop99A#")
    driver.find_element_by_name("email").send_keys(email)
    driver.find_element_by_name("fullName").send_keys("Ankusy Singh")
    
    # Submit registration form
    driver.find_element_by_xpath("//button[@type='submit']").click()
    
    # Enter OTP
    driver.find_element_by_name("verificationCode").send_keys(otp)
    driver.find_element_by_xpath("//button[@type='submit']").click()
    
    driver.quit()

if __name__ == "__main__":
    email = input("Enter your email address: ")
    otp = get_otp(email)
    print(f"OTP received. Creating Instagram account...")
    create_instagram_account(otp)
    print("Instagram account creation completed.")
