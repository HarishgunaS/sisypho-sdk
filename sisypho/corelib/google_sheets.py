"""
Core library for interacting with Google Sheets via MCP server.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

from sisypho.execution.persistent_mcp_client import PersistentMCPClient

def _get_sheets_mcp_client():
    """Get MCP client for Google Sheets integration."""
    sheets_server_path = "../integrations/mcp-google-sheets/src/mcp_google_sheets/server.py"
    mcp_client = PersistentMCPClient(sheets_server_path)
    mcp_client.start()
    return mcp_client

# Data Reading Operations
def get_sheet_data(spreadsheet_id: str, sheet: str, cell_range: Optional[str] = None) -> Dict[str, Any]:
    """
    Get data from a specific sheet in a Google Spreadsheet with full metadata.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL).
        sheet: The name of the sheet.
        cell_range: Optional cell range in A1 notation (e.g., 'A1:C10').
        
    Returns:
        Dict containing grid data structure with full metadata from Google Sheets API.
        
    Examples:
        >>> data = get_sheet_data("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1")
        >>> print(data.keys())
        dict_keys(['spreadsheetId', 'properties', 'sheets'])
        >>> data = get_sheet_data("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", "A1:C10")
        >>> print(len(data['sheets'][0]['data']))
        1
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        
        args = {"spreadsheet_id": spreadsheet_id, "sheet": sheet}
        if cell_range is not None:
            args["range"] = cell_range
            
        result = mcp_client.call_tool_structured("get_sheet_data", args)
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to get sheet data: {e}")
        return {"status": "error", "message": str(e)}

def get_sheet_formulas(spreadsheet_id: str, sheet: str, cell_range: Optional[str] = None) -> List[List[Any]]:
    """
    Get formulas from a specific sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: The name of the sheet.
        cell_range: Optional cell range in A1 notation.
        
    Returns:
        A 2D array of the sheet formulas.
        
    Examples:
        >>> formulas = get_sheet_formulas("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1")
        >>> print(type(formulas))
        <class 'list'>
        >>> formulas = get_sheet_formulas("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", "A1:C10")
        >>> print(len(formulas))
        10
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        
        args = {"spreadsheet_id": spreadsheet_id, "sheet": sheet}
        if cell_range is not None:
            args["range"] = cell_range
            
        result = mcp_client.call_tool_structured("get_sheet_formulas", args)
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"Failed to get sheet formulas: {e}")
        return []

def get_multiple_sheet_data(queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Get data from multiple specific ranges in Google Spreadsheets.
    
    Args:
        queries: List of dictionaries with 'spreadsheet_id', 'sheet', and 'range' keys.
        
    Returns:
        List of dictionaries containing query parameters and fetched data or errors.
        
    Examples:
        >>> queries = [
        ...     {'spreadsheet_id': 'abc123', 'sheet': 'Sheet1', 'range': 'A1:B5'},
        ...     {'spreadsheet_id': 'xyz789', 'sheet': 'Data', 'range': 'C1:C10'}
        ... ]
        >>> results = get_multiple_sheet_data(queries)
        >>> print(len(results))
        2
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("get_multiple_sheet_data", {"queries": queries})
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"Failed to get multiple sheet data: {e}")
        return []

def get_multiple_spreadsheet_summary(spreadsheet_ids: List[str], rows_to_fetch: int = 5) -> List[Dict[str, Any]]:
    """
    Get a summary of multiple Google Spreadsheets with headers and first few rows.
    
    Args:
        spreadsheet_ids: List of spreadsheet IDs to summarize.
        rows_to_fetch: Number of rows including header to fetch (default: 5).
        
    Returns:
        List of dictionaries with spreadsheet summaries.
        
    Examples:
        >>> summaries = get_multiple_spreadsheet_summary(["abc123", "xyz789"], 3)
        >>> print(summaries[0].keys())
        dict_keys(['spreadsheet_id', 'title', 'sheets', 'error'])
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("get_multiple_spreadsheet_summary", {
            "spreadsheet_ids": spreadsheet_ids,
            "rows_to_fetch": rows_to_fetch
        })
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"Failed to get spreadsheet summaries: {e}")
        return []

# Data Writing Operations
def update_cells(spreadsheet_id: str, sheet: str, cell_range: str, data: List[List[Any]]) -> bool:
    """
    Update cells in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: The name of the sheet.
        cell_range: Cell range in A1 notation (e.g., 'A1:C10').
        data: 2D array of values to update.
        
    Returns:
        True if the update was successful, False otherwise.
        
    Examples:
        >>> update_cells("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", "A1:B2", [["Name", "Age"], ["John", 30]])
        True
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("update_cells", {
            "spreadsheet_id": spreadsheet_id,
            "sheet": sheet,
            "range": cell_range,
            "data": data
        })
        
        if result and isinstance(result, dict):
            success = "updatedCells" in result or not result.get("error")
            if not success:
                logger.error(f"Failed to update cells: {result.get('error', 'Unknown error')}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to update cells: {e}")
        return False

def batch_update_cells(spreadsheet_id: str, sheet: str, ranges: Dict[str, List[List[Any]]]) -> bool:
    """
    Batch update multiple ranges in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: The name of the sheet.
        ranges: Dict mapping range strings to 2D arrays of values.
        
    Returns:
        True if the batch update was successful, False otherwise.
        
    Examples:
        >>> ranges = {'A1:B2': [['Name', 'Age'], ['John', 30]], 'D1:E2': [['City', 'Country'], ['NYC', 'USA']]}
        >>> batch_update_cells("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", ranges)
        True
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("batch_update_cells", {
            "spreadsheet_id": spreadsheet_id,
            "sheet": sheet,
            "ranges": ranges
        })
        
        if result and isinstance(result, dict):
            success = "totalUpdatedCells" in result or not result.get("error")
            if not success:
                logger.error(f"Failed to batch update cells: {result.get('error', 'Unknown error')}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to batch update cells: {e}")
        return False

# Sheet Structure Operations
def add_rows(spreadsheet_id: str, sheet: str, count: int, start_row: Optional[int] = None) -> bool:
    """
    Add rows to a sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: The name of the sheet.
        count: Number of rows to add.
        start_row: 0-based row index to start adding. If None, adds at beginning.
        
    Returns:
        True if rows were added successfully, False otherwise.
        
    Examples:
        >>> add_rows("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", 5)
        True
        >>> add_rows("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", 3, 10)
        True
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        
        args = {"spreadsheet_id": spreadsheet_id, "sheet": sheet, "count": count}
        if start_row is not None:
            args["start_row"] = start_row
            
        result = mcp_client.call_tool_structured("add_rows", args)
        
        if result and isinstance(result, dict):
            success = "replies" in result or not result.get("error")
            if not success:
                logger.error(f"Failed to add rows: {result.get('error', 'Unknown error')}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to add rows: {e}")
        return False

def add_columns(spreadsheet_id: str, sheet: str, count: int, start_column: Optional[int] = None) -> bool:
    """
    Add columns to a sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: The name of the sheet.
        count: Number of columns to add.
        start_column: 0-based column index to start adding. If None, adds at beginning.
        
    Returns:
        True if columns were added successfully, False otherwise.
        
    Examples:
        >>> add_columns("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", 3)
        True
        >>> add_columns("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", 2, 5)
        True
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        
        args = {"spreadsheet_id": spreadsheet_id, "sheet": sheet, "count": count}
        if start_column is not None:
            args["start_column"] = start_column
            
        result = mcp_client.call_tool_structured("add_columns", args)
        
        if result and isinstance(result, dict):
            success = "replies" in result or not result.get("error")
            if not success:
                logger.error(f"Failed to add columns: {result.get('error', 'Unknown error')}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to add columns: {e}")
        return False

# Sheet Management Operations
def list_sheets(spreadsheet_id: str) -> List[str]:
    """
    List all sheets in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        
    Returns:
        List of sheet names.
        
    Examples:
        >>> sheets = list_sheets("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        >>> print(sheets)
        ['Sheet1', 'Sheet2', 'Data']
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("list_sheets", {"spreadsheet_id": spreadsheet_id})
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"Failed to list sheets: {e}")
        return []

def copy_sheet(src_spreadsheet: str, src_sheet: str, dst_spreadsheet: str, dst_sheet: str) -> bool:
    """
    Copy a sheet from one spreadsheet to another.
    
    Args:
        src_spreadsheet: Source spreadsheet ID.
        src_sheet: Source sheet name.
        dst_spreadsheet: Destination spreadsheet ID.
        dst_sheet: Destination sheet name.
        
    Returns:
        True if the sheet was copied successfully, False otherwise.
        
    Examples:
        >>> copy_sheet("abc123", "Data", "xyz789", "ImportedData")
        True
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("copy_sheet", {
            "src_spreadsheet": src_spreadsheet,
            "src_sheet": src_sheet,
            "dst_spreadsheet": dst_spreadsheet,
            "dst_sheet": dst_sheet
        })
        
        if result and isinstance(result, dict):
            success = "copy" in result or not result.get("error")
            if not success:
                logger.error(f"Failed to copy sheet: {result.get('error', 'Unknown error')}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to copy sheet: {e}")
        return False

def rename_sheet(spreadsheet_id: str, sheet: str, new_name: str) -> bool:
    """
    Rename a sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: Current sheet name.
        new_name: New sheet name.
        
    Returns:
        True if the sheet was renamed successfully, False otherwise.
        
    Examples:
        >>> rename_sheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", "MainData")
        True
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("rename_sheet", {
            "spreadsheet": spreadsheet_id,
            "sheet": sheet,
            "new_name": new_name
        })
        
        if result and isinstance(result, dict):
            success = "replies" in result or not result.get("error")
            if not success:
                logger.error(f"Failed to rename sheet: {result.get('error', 'Unknown error')}")
            return success
        return False
    except Exception as e:
        logger.error(f"Failed to rename sheet: {e}")
        return False

# Spreadsheet Management Operations
def create_spreadsheet(title: str) -> Dict[str, Any]:
    """
    Create a new Google Spreadsheet.
    
    Args:
        title: The title of the new spreadsheet.
        
    Returns:
        Dict containing information about the newly created spreadsheet.
        
    Examples:
        >>> result = create_spreadsheet("My New Spreadsheet")
        >>> print(result['spreadsheetId'])
        '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("create_spreadsheet", {"title": title})
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to create spreadsheet: {e}")
        return {"status": "error", "message": str(e)}

def create_sheet(spreadsheet_id: str, title: str) -> Dict[str, Any]:
    """
    Create a new sheet tab in an existing Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        title: The title for the new sheet.
        
    Returns:
        Dict containing information about the newly created sheet.
        
    Examples:
        >>> result = create_sheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "NewSheet")
        >>> print(result['title'])
        'NewSheet'
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("create_sheet", {
            "spreadsheet_id": spreadsheet_id,
            "title": title
        })
        return result or {"status": "error", "message": "No response"}
    except Exception as e:
        logger.error(f"Failed to create sheet: {e}")
        return {"status": "error", "message": str(e)}

def list_spreadsheets() -> List[Dict[str, str]]:
    """
    List all spreadsheets in the configured Google Drive folder.
    
    Returns:
        List of spreadsheets with their ID and title.
        
    Examples:
        >>> spreadsheets = list_spreadsheets()
        >>> print(spreadsheets[0].keys())
        dict_keys(['id', 'title'])
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("list_spreadsheets", {})
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"Failed to list spreadsheets: {e}")
        return []

def share_spreadsheet(spreadsheet_id: str, recipients: List[Dict[str, str]], send_notification: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    Share a Google Spreadsheet with multiple users via email.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet to share.
        recipients: List of dicts with 'email_address' and 'role' keys.
                   Role should be 'reader', 'commenter', or 'writer'.
        send_notification: Whether to send notification email (default: True).
        
    Returns:
        Dict containing 'successes' and 'failures' lists.
        
    Examples:
        >>> recipients = [
        ...     {'email_address': 'user1@example.com', 'role': 'writer'},
        ...     {'email_address': 'user2@example.com', 'role': 'reader'}
        ... ]
        >>> result = share_spreadsheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", recipients)
        >>> print(len(result['successes']))
        2
    """
    try:
        mcp_client = _get_sheets_mcp_client()
        result = mcp_client.call_tool_structured("share_spreadsheet", {
            "spreadsheet_id": spreadsheet_id,
            "recipients": recipients,
            "send_notification": send_notification
        })
        return result or {"successes": [], "failures": []}
    except Exception as e:
        logger.error(f"Failed to share spreadsheet: {e}")
        return {"successes": [], "failures": [{"error": str(e)}]}

# Convenience Functions
def append_row(spreadsheet_id: str, sheet: str, row_data: List[Any]) -> bool:
    """
    Append a row to the end of a sheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: The name of the sheet.
        row_data: List of values for the row.
        
    Returns:
        True if the row was appended successfully, False otherwise.
        
    Examples:
        >>> append_row("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", ["John", "Doe", 30])
        True
    """
    try:
        # First, get the current data to find the next empty row
        data = get_sheet_data(spreadsheet_id, sheet)
        if not data or "sheets" not in data:
            return False
            
        # Find the last row with data
        sheets = data.get("sheets", [])
        if not sheets:
            return False
            
        grid_data = sheets[0].get("data", [])
        if not grid_data:
            next_row = 1
        else:
            row_data_list = grid_data[0].get("rowData", [])
            next_row = len(row_data_list) + 1
        
        # Update the next available row
        cell_range = f"A{next_row}:{chr(65 + len(row_data) - 1)}{next_row}"
        return update_cells(spreadsheet_id, sheet, cell_range, [row_data])
    except Exception as e:
        logger.error(f"Failed to append row: {e}")
        return False

def clear_sheet(spreadsheet_id: str, sheet: str, cell_range: Optional[str] = None) -> bool:
    """
    Clear data from a sheet or specific range.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet: The name of the sheet.
        cell_range: Optional specific range to clear. If None, clears entire sheet.
        
    Returns:
        True if the data was cleared successfully, False otherwise.
        
    Examples:
        >>> clear_sheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1")
        True
        >>> clear_sheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "Sheet1", "A1:C10")
        True
    """
    try:
        # Get current data to determine range if not specified
        if cell_range is None:
            data = get_sheet_data(spreadsheet_id, sheet)
            if not data or "sheets" not in data:
                return False
            # Use a large range to clear the entire sheet
            cell_range = "A1:ZZ1000"
        
        # Create empty data array to clear the range
        # First, determine the size of the range to clear
        range_parts = cell_range.split(":")
        if len(range_parts) != 2:
            return False
            
        start_cell, end_cell = range_parts
        
        # Parse start and end positions (simplified - assumes single letter columns)
        start_col = ord(start_cell[0]) - ord('A')
        start_row = int(start_cell[1:]) - 1
        end_col = ord(end_cell[0]) - ord('A')
        end_row = int(end_cell[1:]) - 1
        
        # Create empty data array
        empty_data = [["" for _ in range(end_col - start_col + 1)] 
                     for _ in range(end_row - start_row + 1)]
        
        return update_cells(spreadsheet_id, sheet, cell_range, empty_data)
    except Exception as e:
        logger.error(f"Failed to clear sheet: {e}")
        return False