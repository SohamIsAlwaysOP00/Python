from telethon import TelegramClient
import asyncio
import re

# 1) Fill in your API credentials
api_id = 123456  # replace with your API ID (int)
api_hash = 'your_api_hash'  # replace with your API Hash (string)

# 2) Put the full t.me links for source and target
source_link = 'https://t.me/source_group_or_channel_link'
target_link = 'https://t.me/target_group_or_channel_link'

# Your username with '@' included
my_username = '@AccSellerTGWP'

async def main():
    # Create the client and connect
    client = TelegramClient('tele_copy', api_id, api_hash)
    await client.start()

    # Get the source entity (channel or group)
    source_entity = await client.get_entity(source_link)
    # Get the target entity
    target_entity = await client.get_entity(target_link)

    # Get the full info of the source to find out owner or admins
    source_full = await client(GetFullChannelRequest(source_entity))
    
    # Usually the channel owner is in the list of admins with 'creator' status
    # If you want the exact channel owner, find the creator in admins list:
    from telethon.tl.functions.channels import GetParticipantsRequest
    from telethon.tl.types import ChannelParticipantsCreators, ChannelParticipantAdmin

    # Fetch channel owners/creators/admins
    participants = await client(GetParticipantsRequest(
        channel=source_entity,
        filter=ChannelParticipantsCreators(),
        offset=0,
        limit=10,
        hash=0
    ))
    
    # We assume first creator as the channel owner
    channel_owner = None
    if participants.total > 0:
        channel_owner = participants.users[0]  # Channel owner user object
    
    # Get username of channel owner if available
    channel_owner_username = ''
    if channel_owner and channel_owner.username:
        channel_owner_username = '@' + channel_owner.username
    else:
        # fallback if no username found
        channel_owner_username = ''

    # Iterate through last 100 messages of source channel/group
    async for message in client.iter_messages(source_entity, limit=100):
        # We modify message text if:
        # - The message was sent by the channel owner (check by message.from_id)
        # - AND the message has text
        if message.from_id and channel_owner and message.from_id.user_id == channel_owner.id and message.text:
            # Replace all occurrences of original username with your username
            # Use regex for case insensitive replacement
            # Only replace if channel_owner_username is not empty
            new_text = message.text
            if channel_owner_username:
                new_text = re.sub(re.escape(channel_owner_username), my_username, message.text, flags=re.IGNORECASE)
            else:
                new_text = message.text

            # Send modified message to target
            await client.send_message(target_entity, new_text)
        else:
            # For messages not from channel owner, send as is
            await client.send_message(target_entity, message)

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
  
