import time
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import json

class WhatsAppScraper:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver for WhatsApp Web"""
        chrome_options = Options()
        chrome_options.add_argument("--user-data-dir=./whatsapp_session")  # Save session
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def login_whatsapp(self):
        """Login to WhatsApp Web"""
        print("Opening WhatsApp Web...")
        self.driver.get("https://web.whatsapp.com")
        
        print("Please scan the QR code with your phone to login...")
        
        # Wait for login (QR code scan)
        try:
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']"))
            )
            print("Login successful!")
            time.sleep(3)
        except:
            print("Login timeout. Please try again.")
            return False
        return True
    
    def find_group_by_name(self, group_name):
        """Find and click on a group by name"""
        try:
            # Search for the group
            search_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='chat-list-search']"))
            )
            search_box.click()
            search_box.clear()
            search_box.send_keys(group_name)
            time.sleep(2)
            
            # Click on the group
            group_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//span[@title='{group_name}']"))
            )
            group_element.click()
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Could not find group '{group_name}': {str(e)}")
            return False
    
    def get_group_members(self, group_name):
        """Get all members from a group"""
        if not self.find_group_by_name(group_name):
            return []
        
        try:
            # Click on group header to open group info
            group_header = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='conversation-header']"))
            )
            group_header.click()
            time.sleep(2)
            
            # Click on "View all" participants
            view_all = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'participants')]"))
            )
            view_all.click()
            time.sleep(2)
            
            # Scroll to load all members
            members_container = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='drawer-right']")
            last_height = self.driver.execute_script("return arguments[0].scrollHeight", members_container)
            
            while True:
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", members_container)
                time.sleep(2)
                new_height = self.driver.execute_script("return arguments[0].scrollHeight", members_container)
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Extract member information
            member_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='cell-frame-container']")
            members = []
            
            for element in member_elements:
                try:
                    name_element = element.find_element(By.CSS_SELECTOR, "[data-testid='cell-frame-title']")
                    name = name_element.text
                    if name and name != "You":
                        members.append({"name": name, "element": element})
                except:
                    continue
            
            print(f"Found {len(members)} members in '{group_name}'")
            return members
            
        except Exception as e:
            print(f"Error getting members: {str(e)}")
            return []
    
    def add_members_to_group(self, target_group_name, members):
        """Add members to target group"""
        if not self.find_group_by_name(target_group_name):
            return False
        
        try:
            # Open group info
            group_header = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='conversation-header']"))
            )
            group_header.click()
            time.sleep(2)
            
            # Click "Add participants"
            add_participants = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Add participants')]"))
            )
            add_participants.click()
            time.sleep(2)
            
            added_count = 0
            failed_count = 0
            
            for i, member in enumerate(members, 1):
                try:
                    print(f"Adding member {i}/{len(members)}: {member['name']}")
                    
                    # Search for the member
                    search_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='contact-search-input']")
                    search_input.clear()
                    search_input.send_keys(member['name'])
                    time.sleep(2)
                    
                    # Try to click on the member
                    member_result = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='cell-frame-container']"))
                    )
                    member_result.click()
                    added_count += 1
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Failed to add {member['name']}: {str(e)}")
                    failed_count += 1
                    continue
            
            # Confirm adding members
            try:
                confirm_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='group-invite-ok']"))
                )
                confirm_button.click()
                print("Members addition confirmed!")
            except:
                print("Could not find confirm button, members might have been added individually")
            
            print(f"\n=== Summary ===")
            print(f"Successfully processed: {added_count} members")
            print(f"Failed to add: {failed_count} members")
            print(f"Total attempted: {len(members)} members")
            
            return True
            
        except Exception as e:
            print(f"Error adding members to group: {str(e)}")
            return False
    
    def list_groups(self):
        """List all available groups"""
        try:
            # Get all chat elements
            chat_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='cell-frame-container']")
            groups = []
            
            for element in chat_elements:
                try:
                    # Check if it's a group (has group icon or multiple participants)
                    title_element = element.find_element(By.CSS_SELECTOR, "[data-testid='cell-frame-title']")
                    title = title_element.text
                    
                    # Simple heuristic: groups usually have more than 2 words or contain common group indicators
                    if title and (len(title.split()) > 2 or any(word in title.lower() for word in ['group', 'team', 'family', 'friends'])):
                        groups.append(title)
                except:
                    continue
            
            print(f"\n=== Available Groups ({len(groups)} found) ===")
            for i, group in enumerate(groups, 1):
                print(f"{i}. {group}")
            
            return groups
            
        except Exception as e:
            print(f"Error listing groups: {str(e)}")
            return []
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

def main():
    scraper = WhatsAppScraper()
    
    try:
        # Login to WhatsApp
        if not scraper.login_whatsapp():
            return
        
        print("\nWhatsApp Group Member Transfer Tool")
        print("1. Transfer members between groups")
        print("2. List available groups")
        
        choice = input("Choose option (1 or 2): ")
        
        if choice == "1":
            source_group_name = input("Enter the name of the source group (to copy members from): ")
            target_group_name = input("Enter the name of the target group (to add members to): ")
            
            # Get members from source group
            print(f"Getting members from '{source_group_name}'...")
            members = scraper.get_group_members(source_group_name)
            
            if not members:
                print("No members found or error occurred.")
                return
            
            # Confirm before proceeding
            confirm = input(f"Add {len(members)} members from '{source_group_name}' to '{target_group_name}'? (y/n): ")
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                return
            
            # Add members to target group
            print(f"Adding members to '{target_group_name}'...")
            scraper.add_members_to_group(target_group_name, members)
            
        elif choice == "2":
            scraper.list_groups()
        else:
            print("Invalid choice!")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        input("Press Enter to close the browser...")
        scraper.close()

if __name__ == "__main__":
    main()
