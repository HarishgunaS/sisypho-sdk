"""
Core library for interacting with Gmail via MCP server.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

from execution.persistent_mcp_client import PersistentMCPClient

def _get_gmail_mcp_client():
    """Get MCP client for Gmail integration."""
    gmail_server_path = "../integrations/Gmail-MCP-Server/src/index.ts"
    mcp_client = PersistentMCPClient(gmail_server_path)
    mcp_client.start()
    return mcp_client

# Email Operations
def send_email(to: List[str], 
               subject: str, 
               body: str,
               html_body: Optional[str] = None,
               mime_type: str = "text/plain",
               cc: Optional[List[str]] = None,
               bcc: Optional[List[str]] = None,
               thread_id: Optional[str] = None,
               in_reply_to: Optional[str] = None,
               attachments: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Send a new email.
    
    Args:
        to: List of recipient email addresses.
        subject: Email subject.
        body: Email body content (text/plain or fallback for HTML).
        html_body: HTML version of the email body.
        mime_type: Email content type ('text/plain', 'text/html', 'multipart/alternative').
        cc: List of CC recipients.
        bcc: List of BCC recipients.
        thread_id: Thread ID to reply to.
        in_reply_to: Message ID being replied to.
        attachments: List of file paths to attach.
        
    Returns:
        Dict containing the result of the send operation.
        
    Examples:
        >>> send_email(["user@example.com"], "Test Subject", "Hello World!")
        {'content': [{'type': 'text', 'text': 'Email sent successfully with ID: 123abc'}]}
        >>> send_email(["user@example.com"], "Report", "Please see attachment", 
        ...           attachments=["/path/to/report.pdf"])
        {'content': [{'type': 'text', 'text': 'Email sent successfully with ID: 456def'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        
        args = {
            "to": to,
            "subject": subject,
            "body": body,
            "mimeType": mime_type
        }
        
        if html_body is not None:
            args["htmlBody"] = html_body
        if cc is not None:
            args["cc"] = cc
        if bcc is not None:
            args["bcc"] = bcc
        if thread_id is not None:
            args["threadId"] = thread_id
        if in_reply_to is not None:
            args["inReplyTo"] = in_reply_to
        if attachments is not None:
            args["attachments"] = attachments
            
        result = mcp_client.call_tool_structured("send_email", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"status": "error", "message": str(e)}

def draft_email(to: List[str], 
                subject: str, 
                body: str,
                html_body: Optional[str] = None,
                mime_type: str = "text/plain",
                cc: Optional[List[str]] = None,
                bcc: Optional[List[str]] = None,
                thread_id: Optional[str] = None,
                in_reply_to: Optional[str] = None,
                attachments: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Create an email draft.
    
    Args:
        to: List of recipient email addresses.
        subject: Email subject.
        body: Email body content.
        html_body: HTML version of the email body.
        mime_type: Email content type.
        cc: List of CC recipients.
        bcc: List of BCC recipients.
        thread_id: Thread ID to reply to.
        in_reply_to: Message ID being replied to.
        attachments: List of file paths to attach.
        
    Returns:
        Dict containing the result of the draft operation.
        
    Examples:
        >>> draft_email(["user@example.com"], "Draft Subject", "Draft content")
        {'content': [{'type': 'text', 'text': 'Email draft created successfully with ID: 789ghi'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        
        args = {
            "to": to,
            "subject": subject,
            "body": body,
            "mimeType": mime_type
        }
        
        if html_body is not None:
            args["htmlBody"] = html_body
        if cc is not None:
            args["cc"] = cc
        if bcc is not None:
            args["bcc"] = bcc
        if thread_id is not None:
            args["threadId"] = thread_id
        if in_reply_to is not None:
            args["inReplyTo"] = in_reply_to
        if attachments is not None:
            args["attachments"] = attachments
            
        result = mcp_client.call_tool_structured("draft_email", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to create draft: {e}")
        return {"status": "error", "message": str(e)}

def read_email(message_id: str) -> Dict[str, Any]:
    """
    Retrieve the content of a specific email.
    
    Args:
        message_id: ID of the email message to retrieve.
        
    Returns:
        Dict containing the email content and metadata.
        
    Examples:
        >>> email = read_email("123abc456def")
        >>> print("Subject: " + email['content'][0]['text'].split('\n')[1])
        Subject: Important Meeting
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        result = mcp_client.call_tool_structured("read_email", {"messageId": message_id})
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to read email: {e}")
        return {"status": "error", "message": str(e)}

def search_emails(query: str, max_results: Optional[int] = None) -> Dict[str, Any]:
    """
    Search for emails using Gmail search syntax.
    
    Args:
        query: Gmail search query (e.g., 'from:example@gmail.com').
        max_results: Maximum number of results to return.
        
    Returns:
        Dict containing search results.
        
    Examples:
        >>> results = search_emails("from:boss@company.com", 5)
        >>> print(len(results['content'][0]['text'].split('ID: ')) - 1)
        5
        >>> results = search_emails("has:attachment is:unread")
        >>> print("Found emails with attachments")
        Found emails with attachments
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        
        args = {"query": query}
        if max_results is not None:
            args["maxResults"] = max_results
            
        result = mcp_client.call_tool_structured("search_emails", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to search emails: {e}")
        return {"status": "error", "message": str(e)}

def modify_email(message_id: str,
                 label_ids: Optional[List[str]] = None,
                 add_label_ids: Optional[List[str]] = None,
                 remove_label_ids: Optional[List[str]] = None) -> bool:
    """
    Modify email labels (move to different folders).
    
    Args:
        message_id: ID of the email message to modify.
        label_ids: List of label IDs to apply (replaces existing).
        add_label_ids: List of label IDs to add to the message.
        remove_label_ids: List of label IDs to remove from the message.
        
    Returns:
        True if the email was modified successfully, False otherwise.
        
    Examples:
        >>> modify_email("123abc", add_label_ids=["IMPORTANT"])
        True
        >>> modify_email("456def", remove_label_ids=["INBOX"], add_label_ids=["Label_1"])
        True
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        
        args = {"messageId": message_id}
        if label_ids is not None:
            args["labelIds"] = label_ids
        if add_label_ids is not None:
            args["addLabelIds"] = add_label_ids
        if remove_label_ids is not None:
            args["removeLabelIds"] = remove_label_ids
            
        result = mcp_client.call_tool_structured("modify_email", args)
        
        if result and isinstance(result, dict):
            success = "successfully" in str(result.get("content", [{}])[0].get("text", ""))
            if not success:
                logger.error(f"Failed to modify email: {result}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to modify email: {e}")
        return False

def delete_email(message_id: str) -> bool:
    """
    Permanently delete an email.
    
    Args:
        message_id: ID of the email message to delete.
        
    Returns:
        True if the email was deleted successfully, False otherwise.
        
    Examples:
        >>> delete_email("123abc456def")
        True
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        result = mcp_client.call_tool_structured("delete_email", {"messageId": message_id})
        
        if result and isinstance(result, dict):
            success = "successfully" in str(result.get("content", [{}])[0].get("text", ""))
            if not success:
                logger.error(f"Failed to delete email: {result}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to delete email: {e}")
        return False

def download_attachment(message_id: str, 
                       attachment_id: str,
                       filename: Optional[str] = None,
                       save_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Download an email attachment to a specified location.
    
    Args:
        message_id: ID of the email message containing the attachment.
        attachment_id: ID of the attachment to download.
        filename: Filename to save the attachment as.
        save_path: Directory path to save the attachment.
        
    Returns:
        Dict containing the download result.
        
    Examples:
        >>> download_attachment("123abc", "att_456", "report.pdf", "/downloads")
        {'content': [{'type': 'text', 'text': 'Attachment downloaded successfully...'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        
        args = {
            "messageId": message_id,
            "attachmentId": attachment_id
        }
        
        if filename is not None:
            args["filename"] = filename
        if save_path is not None:
            args["savePath"] = save_path
            
        result = mcp_client.call_tool_structured("download_attachment", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to download attachment: {e}")
        return {"status": "error", "message": str(e)}

# Batch Operations
def batch_modify_emails(message_ids: List[str],
                       add_label_ids: Optional[List[str]] = None,
                       remove_label_ids: Optional[List[str]] = None,
                       batch_size: int = 50) -> Dict[str, Any]:
    """
    Modify labels for multiple emails in batches.
    
    Args:
        message_ids: List of message IDs to modify.
        add_label_ids: List of label IDs to add to all messages.
        remove_label_ids: List of label IDs to remove from all messages.
        batch_size: Number of messages to process in each batch.
        
    Returns:
        Dict containing the batch operation results.
        
    Examples:
        >>> batch_modify_emails(["123", "456", "789"], add_label_ids=["IMPORTANT"])
        {'content': [{'type': 'text', 'text': 'Successfully processed: 3 messages...'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        
        args = {
            "messageIds": message_ids,
            "batchSize": batch_size
        }
        
        if add_label_ids is not None:
            args["addLabelIds"] = add_label_ids
        if remove_label_ids is not None:
            args["removeLabelIds"] = remove_label_ids
            
        result = mcp_client.call_tool_structured("batch_modify_emails", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to batch modify emails: {e}")
        return {"status": "error", "message": str(e)}

def batch_delete_emails(message_ids: List[str], batch_size: int = 50) -> Dict[str, Any]:
    """
    Permanently delete multiple emails in batches.
    
    Args:
        message_ids: List of message IDs to delete.
        batch_size: Number of messages to process in each batch.
        
    Returns:
        Dict containing the batch operation results.
        
    Examples:
        >>> batch_delete_emails(["123", "456", "789"])
        {'content': [{'type': 'text', 'text': 'Successfully deleted: 3 messages...'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        result = mcp_client.call_tool_structured("batch_delete_emails", {
            "messageIds": message_ids,
            "batchSize": batch_size
        })
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to batch delete emails: {e}")
        return {"status": "error", "message": str(e)}

# Label Management
def list_email_labels() -> Dict[str, Any]:
    """
    Retrieve all available Gmail labels.
    
    Returns:
        Dict containing all system and user labels.
        
    Examples:
        >>> labels = list_email_labels()
        >>> print("Found labels:" in labels['content'][0]['text'])
        True
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        result = mcp_client.call_tool_structured("list_email_labels", {})
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to list labels: {e}")
        return {"status": "error", "message": str(e)}

def create_label(name: str,
                 message_list_visibility: str = "show",
                 label_list_visibility: str = "labelShow") -> Dict[str, Any]:
    """
    Create a new Gmail label.
    
    Args:
        name: Name for the new label.
        message_list_visibility: Whether to show or hide the label in message list ('show', 'hide').
        label_list_visibility: Visibility in label list ('labelShow', 'labelShowIfUnread', 'labelHide').
        
    Returns:
        Dict containing the created label information.
        
    Examples:
        >>> create_label("Important Projects")
        {'content': [{'type': 'text', 'text': 'Label created successfully:\nID: Label_123...'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        result = mcp_client.call_tool_structured("create_label", {
            "name": name,
            "messageListVisibility": message_list_visibility,
            "labelListVisibility": label_list_visibility
        })
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to create label: {e}")
        return {"status": "error", "message": str(e)}

def update_label(label_id: str,
                 name: Optional[str] = None,
                 message_list_visibility: Optional[str] = None,
                 label_list_visibility: Optional[str] = None) -> Dict[str, Any]:
    """
    Update an existing Gmail label.
    
    Args:
        label_id: ID of the label to update.
        name: New name for the label.
        message_list_visibility: Message list visibility setting.
        label_list_visibility: Label list visibility setting.
        
    Returns:
        Dict containing the updated label information.
        
    Examples:
        >>> update_label("Label_123", name="Updated Project Name")
        {'content': [{'type': 'text', 'text': 'Label updated successfully:\nID: Label_123...'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        
        args = {"id": label_id}
        if name is not None:
            args["name"] = name
        if message_list_visibility is not None:
            args["messageListVisibility"] = message_list_visibility
        if label_list_visibility is not None:
            args["labelListVisibility"] = label_list_visibility
            
        result = mcp_client.call_tool_structured("update_label", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to update label: {e}")
        return {"status": "error", "message": str(e)}

def delete_label(label_id: str) -> bool:
    """
    Delete a Gmail label.
    
    Args:
        label_id: ID of the label to delete.
        
    Returns:
        True if the label was deleted successfully, False otherwise.
        
    Examples:
        >>> delete_label("Label_123")
        True
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        result = mcp_client.call_tool_structured("delete_label", {"id": label_id})
        
        if result and isinstance(result, dict):
            success = "successfully" in str(result.get("content", [{}])[0].get("text", ""))
            if not success:
                logger.error(f"Failed to delete label: {result}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to delete label: {e}")
        return False

def get_or_create_label(name: str,
                       message_list_visibility: str = "show",
                       label_list_visibility: str = "labelShow") -> Dict[str, Any]:
    """
    Get an existing label by name or create it if it doesn't exist.
    
    Args:
        name: Name of the label to get or create.
        message_list_visibility: Message list visibility setting.
        label_list_visibility: Label list visibility setting.
        
    Returns:
        Dict containing the label information.
        
    Examples:
        >>> get_or_create_label("Auto Archive")
        {'content': [{'type': 'text', 'text': 'Successfully found existing label:\nID: Label_456...'}]}
    """
    try:
        mcp_client = _get_gmail_mcp_client()
        result = mcp_client.call_tool_structured("get_or_create_label", {
            "name": name,
            "messageListVisibility": message_list_visibility,
            "labelListVisibility": label_list_visibility
        })
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to get or create label: {e}")
        return {"status": "error", "message": str(e)}

# Convenience Functions
def send_simple_email(to: str, subject: str, body: str) -> bool:
    """
    Send a simple text email to a single recipient.
    
    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email body content.
        
    Returns:
        True if the email was sent successfully, False otherwise.
        
    Examples:
        >>> send_simple_email("user@example.com", "Hello", "How are you?")
        True
    """
    result = send_email([to], subject, body)
    return "successfully" in str(result.get("content", [{}])[0].get("text", ""))

def reply_to_email(original_message_id: str, to: List[str], subject: str, body: str, thread_id: str) -> bool:
    """
    Reply to an existing email.
    
    Args:
        original_message_id: ID of the message being replied to.
        to: Recipients for the reply.
        subject: Subject for the reply.
        body: Body content for the reply.
        thread_id: Thread ID to maintain conversation.
        
    Returns:
        True if the reply was sent successfully, False otherwise.
        
    Examples:
        >>> reply_to_email("123abc", ["user@example.com"], "Re: Meeting", "I'll be there!", "thread_456")
        True
    """
    result = send_email(to, subject, body, thread_id=thread_id, in_reply_to=original_message_id)
    return "successfully" in str(result.get("content", [{}])[0].get("text", ""))

def archive_emails(message_ids: List[str]) -> bool:
    """
    Archive multiple emails by removing them from INBOX.
    
    Args:
        message_ids: List of message IDs to archive.
        
    Returns:
        True if emails were archived successfully, False otherwise.
        
    Examples:
        >>> archive_emails(["123", "456", "789"])
        True
    """
    result = batch_modify_emails(message_ids, remove_label_ids=["INBOX"])
    return "Successfully processed" in str(result.get("content", [{}])[0].get("text", ""))

def mark_as_read(message_ids: List[str]) -> bool:
    """
    Mark multiple emails as read.
    
    Args:
        message_ids: List of message IDs to mark as read.
        
    Returns:
        True if emails were marked as read successfully, False otherwise.
        
    Examples:
        >>> mark_as_read(["123", "456"])
        True
    """
    result = batch_modify_emails(message_ids, remove_label_ids=["UNREAD"])
    return "Successfully processed" in str(result.get("content", [{}])[0].get("text", ""))

def mark_as_important(message_ids: List[str]) -> bool:
    """
    Mark multiple emails as important.
    
    Args:
        message_ids: List of message IDs to mark as important.
        
    Returns:
        True if emails were marked as important successfully, False otherwise.
        
    Examples:
        >>> mark_as_important(["123", "456"])
        True
    """
    result = batch_modify_emails(message_ids, add_label_ids=["IMPORTANT"])
    return "Successfully processed" in str(result.get("content", [{}])[0].get("text", ""))