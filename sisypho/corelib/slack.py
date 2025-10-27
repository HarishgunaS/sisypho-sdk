"""
Core library for interacting with Slack via MCP server.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

from sisypho.execution.persistent_mcp_client import PersistentMCPClient

def _get_slack_mcp_client():
    """Get MCP client for Slack integration."""
    slack_server_path = "../integrations/slack-mcp-server/cmd/slack-mcp-server/main.go"
    mcp_client = PersistentMCPClient(slack_server_path)
    mcp_client.start()
    return mcp_client

# Conversation Operations
def get_conversation_history(channel_id: str,
                           include_activity_messages: bool = False,
                           cursor: Optional[str] = None,
                           limit: str = "1d") -> Dict[str, Any]:
    """
    Get messages from a channel or DM by channel_id.
    
    Args:
        channel_id: ID of the channel in format Cxxxxxxxxxx or its name starting with #... or @... aka #general or @username_dm.
        include_activity_messages: If true, includes activity messages such as 'channel_join' or 'channel_leave'. Default is False.
        cursor: Cursor for pagination. Use the value from the last row/column in previous response.
        limit: Limit of messages to fetch in format of maximum ranges of time (e.g. 1d - 1 day, 1w - 1 week, 30d - 30 days, 90d - 90 days) or number of messages (e.g. 50). Must be empty when 'cursor' is provided.
        
    Returns:
        Dict containing channel messages and metadata.
        
    Examples:
        >>> history = get_conversation_history("#general", limit="50")
        >>> print("Messages found" in str(history))
        True
        >>> history = get_conversation_history("C123456789", include_activity_messages=True)
        >>> print("Channel activity included" in str(history))
        True
    """
    try:
        mcp_client = _get_slack_mcp_client()
        
        args = {
            "channel_id": channel_id,
            "include_activity_messages": include_activity_messages,
            "limit": limit
        }
        
        if cursor is not None:
            args["cursor"] = cursor
            
        result = mcp_client.call_tool_structured("conversations_history", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        return {"status": "error", "message": str(e)}

def get_conversation_replies(channel_id: str,
                           thread_ts: str,
                           include_activity_messages: bool = False,
                           cursor: Optional[str] = None,
                           limit: str = "1d") -> Dict[str, Any]:
    """
    Get a thread of messages posted to a conversation by channelID and thread_ts.
    
    Args:
        channel_id: ID of the channel in format Cxxxxxxxxxx or its name starting with #... or @... aka #general or @username_dm.
        thread_ts: Unique identifier of either a thread's parent message or a message in the thread. ts must be the timestamp in format 1234567890.123456 of an existing message with 0 or more replies.
        include_activity_messages: If true, includes activity messages such as 'channel_join' or 'channel_leave'. Default is False.
        cursor: Cursor for pagination. Use the value from the last row/column in previous response.
        limit: Limit of messages to fetch in format of maximum ranges of time (e.g. 1d - 1 day, 30d - 30 days, 90d - 90 days) or number of messages (e.g. 50). Must be empty when 'cursor' is provided.
        
    Returns:
        Dict containing thread messages and metadata.
        
    Examples:
        >>> replies = get_conversation_replies("#general", "1234567890.123456")
        >>> print("Thread replies found" in str(replies))
        True
        >>> replies = get_conversation_replies("C123456789", "1234567890.123456", limit="10")
        >>> print("Limited thread replies" in str(replies))
        True
    """
    try:
        mcp_client = _get_slack_mcp_client()
        
        args = {
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "include_activity_messages": include_activity_messages,
            "limit": limit
        }
        
        if cursor is not None:
            args["cursor"] = cursor
            
        result = mcp_client.call_tool_structured("conversations_replies", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to get conversation replies: {e}")
        return {"status": "error", "message": str(e)}

def add_message_to_conversation(channel_id: str,
                              payload: str,
                              thread_ts: Optional[str] = None,
                              content_type: str = "text/markdown") -> bool:
    """
    Add a message to a public channel, private channel, or direct message (DM, or IM) conversation.
    
    Args:
        channel_id: ID of the channel in format Cxxxxxxxxxx or its name starting with #... or @... aka #general or @username_dm.
        payload: Message payload in specified content_type format. Example: 'Hello, world!' for text/plain or '# Hello, world!' for text/markdown.
        thread_ts: Unique identifier of either a thread's parent message or a message in the thread. Optional, if not provided the message will be added to the channel itself, otherwise it will be added to the thread.
        content_type: Content type of the message. Default is 'text/markdown'. Allowed values: 'text/markdown', 'text/plain'.
        
    Returns:
        True if the message was added successfully, False otherwise.
        
    Examples:
        >>> add_message_to_conversation("#general", "Hello team!")
        True
        >>> add_message_to_conversation("C123456789", "**Important update**", content_type="text/markdown")
        True
        >>> add_message_to_conversation("#general", "Thread reply", thread_ts="1234567890.123456")
        True
    """
    try:
        mcp_client = _get_slack_mcp_client()
        
        args = {
            "channel_id": channel_id,
            "payload": payload,
            "content_type": content_type
        }
        
        if thread_ts is not None:
            args["thread_ts"] = thread_ts
            
        result = mcp_client.call_tool_structured("conversations_add_message", args)
        
        if result and isinstance(result, dict):
            success = "successfully" in str(result.get("content", [{}])[0].get("text", "")).lower()
            if not success:
                logger.error(f"Failed to add message: {result}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        return False

def search_messages(search_query: Optional[str] = None,
                   filter_in_channel: Optional[str] = None,
                   filter_in_im_or_mpim: Optional[str] = None,
                   filter_users_with: Optional[str] = None,
                   filter_users_from: Optional[str] = None,
                   filter_date_before: Optional[str] = None,
                   filter_date_after: Optional[str] = None,
                   filter_date_on: Optional[str] = None,
                   filter_date_during: Optional[str] = None,
                   filter_threads_only: bool = False,
                   cursor: str = "",
                   limit: int = 20) -> Dict[str, Any]:
    """
    Search messages in channels, DMs, or across the workspace using filters.
    
    Args:
        search_query: Search query to filter messages. Example: 'marketing report' or full URL of Slack message.
        filter_in_channel: Filter messages in a specific channel by its ID or name. Example: 'C1234567890' or '#general'.
        filter_in_im_or_mpim: Filter messages in a direct message (DM) or multi-person direct message (MPIM) conversation by its ID or name. Example: 'D1234567890' or '@username_dm'.
        filter_users_with: Filter messages with a specific user by their ID or display name in threads and DMs. Example: 'U1234567890' or '@username'.
        filter_users_from: Filter messages from a specific user by their ID or display name. Example: 'U1234567890' or '@username'.
        filter_date_before: Filter messages sent before a specific date in format 'YYYY-MM-DD'. Example: '2023-10-01', 'July', 'Yesterday' or 'Today'.
        filter_date_after: Filter messages sent after a specific date in format 'YYYY-MM-DD'. Example: '2023-10-01', 'July', 'Yesterday' or 'Today'.
        filter_date_on: Filter messages sent on a specific date in format 'YYYY-MM-DD'. Example: '2023-10-01', 'July', 'Yesterday' or 'Today'.
        filter_date_during: Filter messages sent during a specific period in format 'YYYY-MM-DD'. Example: 'July', 'Yesterday' or 'Today'.
        filter_threads_only: If true, the response will include only messages from threads. Default is False.
        cursor: Cursor for pagination. Use the value from the last row/column in previous response.
        limit: The maximum number of items to return. Must be an integer between 1 and 100.
        
    Returns:
        Dict containing search results and metadata.
        
    Examples:
        >>> results = search_messages("project update", limit=10)
        >>> print("Search results found" in str(results))
        True
        >>> results = search_messages(filter_in_channel="#engineering", filter_users_from="@john")
        >>> print("Filtered search results" in str(results))
        True
        >>> results = search_messages(filter_date_after="2023-01-01", filter_threads_only=True)
        >>> print("Thread-only search results" in str(results))
        True
    """
    try:
        mcp_client = _get_slack_mcp_client()
        
        args = {
            "cursor": cursor,
            "limit": limit,
            "filter_threads_only": filter_threads_only
        }
        
        if search_query is not None:
            args["search_query"] = search_query
        if filter_in_channel is not None:
            args["filter_in_channel"] = filter_in_channel
        if filter_in_im_or_mpim is not None:
            args["filter_in_im_or_mpim"] = filter_in_im_or_mpim
        if filter_users_with is not None:
            args["filter_users_with"] = filter_users_with
        if filter_users_from is not None:
            args["filter_users_from"] = filter_users_from
        if filter_date_before is not None:
            args["filter_date_before"] = filter_date_before
        if filter_date_after is not None:
            args["filter_date_after"] = filter_date_after
        if filter_date_on is not None:
            args["filter_date_on"] = filter_date_on
        if filter_date_during is not None:
            args["filter_date_during"] = filter_date_during
            
        result = mcp_client.call_tool_structured("conversations_search_messages", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to search messages: {e}")
        return {"status": "error", "message": str(e)}

# Channel Operations
def list_channels(channel_types: str,
                 sort: Optional[str] = None,
                 limit: int = 100,
                 cursor: Optional[str] = None) -> Dict[str, Any]:
    """
    Get list of channels by type.
    
    Args:
        channel_types: Comma-separated channel types. Allowed values: 'mpim', 'im', 'public_channel', 'private_channel'. Example: 'public_channel,private_channel,im'.
        sort: Type of sorting. Allowed values: 'popularity' - sort by number of members/participants in each channel.
        limit: The maximum number of items to return. Must be an integer between 1 and 1000 (maximum 999).
        cursor: Cursor for pagination. Use the value from the last row/column in previous response.
        
    Returns:
        Dict containing channel list and metadata.
        
    Examples:
        >>> channels = list_channels("public_channel,private_channel")
        >>> print("Channels found" in str(channels))
        True
        >>> channels = list_channels("im", sort="popularity", limit=50)
        >>> print("Direct messages sorted by popularity" in str(channels))
        True
        >>> channels = list_channels("public_channel", limit=10)
        >>> print("Limited public channels" in str(channels))
        True
    """
    try:
        mcp_client = _get_slack_mcp_client()
        
        args = {
            "channel_types": channel_types,
            "limit": limit
        }
        
        if sort is not None:
            args["sort"] = sort
        if cursor is not None:
            args["cursor"] = cursor
            
        result = mcp_client.call_tool_structured("channels_list", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to list channels: {e}")
        return {"status": "error", "message": str(e)}

# Convenience Functions
def send_simple_message(channel: str, message: str) -> bool:
    """
    Send a simple text message to a channel or DM.
    
    Args:
        channel: Channel name (e.g., '#general') or ID (e.g., 'C123456789') or DM (@username_dm).
        message: The message text to send.
        
    Returns:
        True if the message was sent successfully, False otherwise.
        
    Examples:
        >>> send_simple_message("#general", "Hello everyone!")
        True
        >>> send_simple_message("@john_dm", "Hi John, how are you?")
        True
    """
    return add_message_to_conversation(channel, message, content_type="text/plain")

def send_markdown_message(channel: str, message: str) -> bool:
    """
    Send a markdown-formatted message to a channel or DM.
    
    Args:
        channel: Channel name (e.g., '#general') or ID (e.g., 'C123456789') or DM (@username_dm).
        message: The markdown-formatted message text to send.
        
    Returns:
        True if the message was sent successfully, False otherwise.
        
    Examples:
        >>> send_markdown_message("#general", "**Important:** Please review the *quarterly report*")
        True
        >>> send_markdown_message("#dev", "```python\\nprint('Hello, World!')\\n```")
        True
    """
    return add_message_to_conversation(channel, message, content_type="text/markdown")

def reply_to_thread(channel: str, thread_ts: str, message: str, content_type: str = "text/plain") -> bool:
    """
    Reply to an existing thread in a channel.
    
    Args:
        channel: Channel name (e.g., '#general') or ID (e.g., 'C123456789').
        thread_ts: Timestamp of the parent message or any message in the thread.
        message: The reply message text.
        content_type: Content type ('text/plain' or 'text/markdown').
        
    Returns:
        True if the reply was sent successfully, False otherwise.
        
    Examples:
        >>> reply_to_thread("#general", "1234567890.123456", "Thanks for the update!")
        True
        >>> reply_to_thread("#dev", "1234567890.123456", "**Fixed** in PR #123", "text/markdown")
        True
    """
    return add_message_to_conversation(channel, message, thread_ts=thread_ts, content_type=content_type)

def get_public_channels(limit: int = 100) -> Dict[str, Any]:
    """
    Get list of public channels.
    
    Args:
        limit: Maximum number of channels to return.
        
    Returns:
        Dict containing public channel list.
        
    Examples:
        >>> channels = get_public_channels(50)
        >>> print("Public channels found" in str(channels))
        True
    """
    return list_channels("public_channel", limit=limit)

def get_private_channels(limit: int = 100) -> Dict[str, Any]:
    """
    Get list of private channels the user has access to.
    
    Args:
        limit: Maximum number of channels to return.
        
    Returns:
        Dict containing private channel list.
        
    Examples:
        >>> channels = get_private_channels(25)
        >>> print("Private channels found" in str(channels))
        True
    """
    return list_channels("private_channel", limit=limit)

def get_direct_messages(limit: int = 100) -> Dict[str, Any]:
    """
    Get list of direct message conversations.
    
    Args:
        limit: Maximum number of DM conversations to return.
        
    Returns:
        Dict containing DM conversation list.
        
    Examples:
        >>> dms = get_direct_messages(30)
        >>> print("Direct messages found" in str(dms))
        True
    """
    return list_channels("im", limit=limit)

def search_recent_messages(query: str, days: int = 7) -> Dict[str, Any]:
    """
    Search for messages from the last N days.
    
    Args:
        query: Search query string.
        days: Number of days to search back (1-90).
        
    Returns:
        Dict containing search results.
        
    Examples:
        >>> results = search_recent_messages("project status", 3)
        >>> print("Recent search results" in str(results))
        True
    """
    filter_date = f"{days}d"
    return search_messages(search_query=query, filter_date_during=filter_date)

def get_channel_messages(channel: str, message_count: int = 50) -> Dict[str, Any]:
    """
    Get recent messages from a specific channel.
    
    Args:
        channel: Channel name (e.g., '#general') or ID (e.g., 'C123456789').
        message_count: Number of messages to retrieve (1-100).
        
    Returns:
        Dict containing channel messages.
        
    Examples:
        >>> messages = get_channel_messages("#general", 20)
        >>> print("Channel messages retrieved" in str(messages))
        True
    """
    return get_conversation_history(channel, limit=str(message_count))

def get_user_messages(username: str, days: int = 30) -> Dict[str, Any]:
    """
    Get messages from a specific user in the last N days.
    
    Args:
        username: Username to search for (e.g., '@john' or 'U123456789').
        days: Number of days to search back.
        
    Returns:
        Dict containing user's messages.
        
    Examples:
        >>> messages = get_user_messages("@john", 7)
        >>> print("User messages found" in str(messages))
        True
    """
    filter_date = f"{days}d"
    return search_messages(filter_users_from=username, filter_date_during=filter_date)

def search_in_channel(channel: str, query: str) -> Dict[str, Any]:
    """
    Search for messages within a specific channel.
    
    Args:
        channel: Channel name (e.g., '#general') or ID (e.g., 'C123456789').
        query: Search query string.
        
    Returns:
        Dict containing search results from the channel.
        
    Examples:
        >>> results = search_in_channel("#engineering", "deployment")
        >>> print("Channel-specific search results" in str(results))
        True
    """
    return search_messages(search_query=query, filter_in_channel=channel)