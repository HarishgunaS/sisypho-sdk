"""
Core library for interacting with Google Drive and Google Sheets.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

from ..execution.persistent_mcp_client import PersistentMCPClient

def _get_gdrive_mcp_client():
    """Get MCP client for Google Drive/Sheets integration."""
    gdrive_server_path = "../integrations/mcp-gdrive/dist/index.js"
    mcp_client = PersistentMCPClient(gdrive_server_path)
    mcp_client.start()
    return mcp_client

# Google Drive Operations
def search_drive(query: str, page_token: Optional[str] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
    """
    Search for files in Google Drive.
    
    Args:
        query: Search query string to find files.
        page_token: Optional token for pagination.
        page_size: Optional number of results per page.
        
    Returns:
        Dict containing search results or error status.
        
    Examples:
        >>> results = search_drive("type:spreadsheet")
        >>> print(results['status'])
        'success'
        >>> results = search_drive("name:budget", page_size=10)
        >>> print(len(results['files']))
        5
    """
    try:
        mcp_client = _get_gdrive_mcp_client()
        
        args = {"query": query}
        if page_token is not None:
            args["pageToken"] = page_token
        if page_size is not None:
            args["pageSize"] = page_size
            
        result = mcp_client.call_tool_structured("gdrive_search", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to search Google Drive: {e}")
        return {"status": "error", "message": str(e)}

def read_drive_file(file_id: str) -> Dict[str, Any]:
    """
    Read a file from Google Drive.
    
    Args:
        file_id: The ID of the file to read.
        
    Returns:
        Dict containing file content or error status.
        
    Examples:
        >>> content = read_drive_file("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        >>> print(content['status'])
        'success'
    """
    try:
        mcp_client = _get_gdrive_mcp_client()
        result = mcp_client.call_tool_structured("gdrive_read_file", {"fileId": file_id})
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to read Google Drive file '{file_id}': {e}")
        return {"status": "error", "message": str(e)}

# Google Sheets Operations
def read_sheet(spreadsheet_id: str, ranges: Optional[List[str]] = None, sheet_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Read data from a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet to read.
        ranges: Optional list of A1 notation ranges like ['Sheet1!A1:B10'].
        sheet_id: Optional specific sheet ID to read.
        
    Returns:
        Dict containing spreadsheet data or error status.
        
    Examples:
        >>> data = read_sheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        >>> print(data['status'])
        'success'
        >>> data = read_sheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", ranges=["Sheet1!A1:C10"])
        >>> print(len(data['sheets']))
        1
    """
    try:
        mcp_client = _get_gdrive_mcp_client()
        
        args = {"spreadsheetId": spreadsheet_id}
        if ranges is not None:
            args["ranges"] = ranges
        if sheet_id is not None:
            args["sheetId"] = sheet_id
            
        result = mcp_client.call_tool_structured("gsheets_read", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to read Google Sheet '{spreadsheet_id}': {e}")
        return {"status": "error", "message": str(e)}

def update_sheet_cell(spreadsheet_id: str, cell_range: str, value: str) -> bool:
    """
    Update a cell value in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet to update.
        cell_range: Cell range in A1 notation (e.g. 'Sheet1!A1').
        value: New cell value to set.
        
    Returns:
        True if the cell was updated successfully, False otherwise.
        
    Examples:
        >>> update_sheet_cell("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1!A1", "Hello World")
        True
        >>> update_sheet_cell("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Budget!B2", "150.00")
        True
    """
    try:
        mcp_client = _get_gdrive_mcp_client()
        result = mcp_client.call_tool_structured("gsheets_update_cell", {
            "fileId": spreadsheet_id,
            "range": cell_range,
            "value": value
        })
        
        if result and isinstance(result, dict):
            success = result.get("status") == "success" or not result.get("isError", True)
            if not success:
                logger.error(f"Failed to update cell '{cell_range}': {result.get('message', 'Unknown error')}")
            return success
        else:
            logger.error("Invalid result format from gsheets_update_cell")
            return False
    except Exception as e:
        logger.error(f"Failed to update Google Sheet cell '{cell_range}': {e}")
        return False

# Convenience functions for common operations
def create_sheet_row(spreadsheet_id: str, sheet_name: str, row_data: List[str], start_row: int = 1) -> bool:
    """
    Create/update a row in a Google Sheet by updating multiple cells.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet_name: Name of the sheet (e.g. 'Sheet1').
        row_data: List of values for the row.
        start_row: Row number to start from (1-based).
        
    Returns:
        True if all cells were updated successfully, False otherwise.
        
    Examples:
        >>> create_sheet_row("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", ["John", "Doe", "30"], 2)
        True
    """
    try:
        # Update each cell in the row
        for col_index, value in enumerate(row_data):
            # Convert column index to letter (0->A, 1->B, etc.)
            col_letter = chr(65 + col_index)
            cell_range = f"{sheet_name}!{col_letter}{start_row}"
            
            if not update_sheet_cell(spreadsheet_id, cell_range, str(value)):
                return False
                
        return True
    except Exception as e:
        logger.error(f"Failed to create sheet row: {e}")
        return False

def find_files_by_name(name: str, file_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Find files in Google Drive by name.
    
    Args:
        name: Name or partial name to search for.
        file_type: Optional file type filter ('spreadsheet', 'document', 'folder', etc.).
        
    Returns:
        Dict containing search results or error status.
        
    Examples:
        >>> files = find_files_by_name("budget")
        >>> print(len(files['files']))
        3
        >>> spreadsheets = find_files_by_name("report", "spreadsheet")
        >>> print(spreadsheets['status'])
        'success'
    """
    query = f"name contains '{name}'"
    if file_type:
        query += f" and mimeType contains '{file_type}'"
    
    return search_drive(query)