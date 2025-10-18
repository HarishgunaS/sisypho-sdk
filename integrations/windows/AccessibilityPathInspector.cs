using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Automation;

#region IAccessible COM Interface

[ComImport, Guid("618736E0-3C3D-11CF-810C-00AA00389B71")]
[InterfaceType(ComInterfaceType.InterfaceIsDual)]
public interface IAccessible
{
    [DispId(-5000)]
    void get_accParent([MarshalAs(UnmanagedType.IDispatch)] out object ppdispParent);

    [DispId(-5001)]
    int get_accChildCount();

    [DispId(-5003)]
    void get_accName([In, Optional, MarshalAs(UnmanagedType.Struct)] object varChild,
                     [MarshalAs(UnmanagedType.BStr)] out object pszName);

    [DispId(-5004)]
    void get_accRole([In, Optional, MarshalAs(UnmanagedType.Struct)] object varChild,
                     [MarshalAs(UnmanagedType.Struct)] out object pvarRole);

    [DispId(-5005)]
    void get_accValue([In, Optional, MarshalAs(UnmanagedType.Struct)] object varChild,
                      [MarshalAs(UnmanagedType.BStr)] out string pszValue);

    [DispId(-5006)]
    void put_accName([In, Optional, MarshalAs(UnmanagedType.Struct)] object varChild,
                     [In, MarshalAs(UnmanagedType.BStr)] string pszName);

    [DispId(-5007)]
    void put_accValue([In, Optional, MarshalAs(UnmanagedType.Struct)] object varChild,
                      [In, MarshalAs(UnmanagedType.BStr)] string pszValue);
}

#endregion

#region Native Methods

public struct POINT
{
    public int x;
    public int y;
}

public static class NativeMethods
{
    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT lpPoint);

    [DllImport("oleacc.dll")]
    public static extern int AccessibleObjectFromPoint(
        POINT pt,
        [Out, MarshalAs(UnmanagedType.Interface)] out IAccessible ppacc,
        [Out, MarshalAs(UnmanagedType.Struct)] out object pvarChild);
}

#endregion

public static class AccessibilityPathInspector
{
    /// <summary>Inspect the element currently under the mouse cursor.</summary>
    public static void InspectAtCursor()
    {
        NativeMethods.GetCursorPos(out POINT p);
        InspectAtPoint(p.x, p.y);
    }

    /// <summary>Inspect the element at a specific screen coordinate.</summary>
    public static void InspectAtPoint(int x, int y)
    {
        var point = new System.Windows.Point(x, y);
        var element = AutomationElement.FromPoint(point);

        Console.WriteLine($"[UIA] Target element: {element?.Current.Name ?? "(null)"} | {element?.Current.ClassName}");

        // Try UIA path first
        var uiaPath = GetUIAPathToRoot(element);
        if (uiaPath != null && uiaPath.Count > 1)
        {
            Console.WriteLine("\n[UIA Path to Root]");
            DumpUIAPath(uiaPath);
            // return;
        }

        // Fallback to MSAA
        Console.WriteLine("[UIA] Limited info or Electron app detected. Trying MSAA fallback...\n");
        GetMSAAPathToRoot(x, y);
    }

    #region UIA Path

    private static List<AutomationElement> GetUIAPathToRoot(AutomationElement element)
    {
        var list = new List<AutomationElement>();
        while (element != null)
        {
            list.Add(element);
            try
            {
                element = TreeWalker.RawViewWalker.GetParent(element);
            }
            catch
            {
                break;
            }
        }
        return list;
    }

    private static void DumpUIAPath(List<AutomationElement> path)
    {
        for (int i = 0; i < path.Count; i++)
        {
            var el = path[i];
            Console.WriteLine($"[{i}] {el.Current.ControlType?.ProgrammaticName ?? "Unknown"} | \"{el.Current.Name}\" | {el.Current.ClassName}");
        }
    }

    #endregion

    #region MSAA Path

    private static void GetMSAAPathToRoot(int x, int y)
    {
        var pt = new POINT { x = x, y = y };
        int hr = NativeMethods.AccessibleObjectFromPoint(pt, out IAccessible acc, out object child);

        if (hr < 0 || acc == null)
        {
            Console.WriteLine("[MSAA] Could not get accessible object from point.");
            return;
        }

        var path = new List<IAccessible>();
        object parent = acc;

        while (parent is IAccessible current)
        {
            path.Add(current);
            current.get_accParent(out parent);
        }

        Console.WriteLine("[MSAA Path to Root]");
        DumpMSAAPath(path);
    }

    private static void DumpMSAAPath(List<IAccessible> path)
    {
        for (int i = 0; i < path.Count; i++)
        {
            try
            {
                path[i].get_accName(null, out object nameObj);
                string name = nameObj as string ?? "(null)";
                path[i].get_accRole(null, out object roleObj);
                string role = (roleObj != null) ? roleObj.ToString() : "(null)";
                Console.WriteLine($"[{i}] Role={role} | Name=\"{name}\"");
            }
            catch (Exception) 
            { 
              Console.WriteLine($"[{i}] (failed to get name/role)");
            }
        }
    }

    #endregion
}
