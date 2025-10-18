using System;
using System.Collections.Generic;
using System.Windows.Automation;
using SharpHook;

class Program
{
    static void Main()
    {
        Console.WriteLine("Starting UI Automation + SharpHook example...");

        // Get desktop root element
        AutomationElement root = AutomationElement.RootElement;
        Console.WriteLine("Root element: " + root.Current);

        // Initialize SharpHook event loop
        var hook = new EventLoopGlobalHook();

        // MouseClicked
        hook.MouseClicked += (s, e) =>
        {
            PrintEventWithClickedElement(e, root);
        };

        // KeyPressed
        hook.KeyPressed += (s, e) =>
        {
            PrintEventWithFocusedElement("Key pressed", root);
        };

        // KeyReleased
        hook.KeyReleased += (s, e) =>
        {
            PrintEventWithFocusedElement("Key released", root);
        };

        Console.WriteLine("Listening for keyboard and mouse events...");
        hook.Run();
    }

    // Helper method to print event + currently focused UI element
    static void PrintEventWithFocusedElement(string eventName, AutomationElement root)
    {
        AutomationElement focusedElement = AutomationElement.FocusedElement;

        string name = focusedElement?.Current.Name ?? "<unnamed element>";
        string controlType = focusedElement?.Current.ControlType?.ProgrammaticName ?? "<unknown type>";
        Console.WriteLine($"{eventName}: focused element = {name}, type = {controlType}");
    }
    static void PrintEventWithClickedElement(MouseHookEventArgs args, AutomationElement root)
    {
        
        System.Windows.Point point = new System.Windows.Point(args.Data.X, args.Data.Y);
        AccessibilityPathInspector.InspectAtPoint(args.Data.X, args.Data.Y);

        AutomationElement focusedElement = AutomationElement.FromPoint(point);

        string name = focusedElement?.Current.Name ?? "<unnamed element>";
        string controlType = focusedElement?.Current.ControlType?.ProgrammaticName ?? "<unknown type>";
        string path = GetElementPath(focusedElement);
        Console.WriteLine($"Element clicked = {path}");
        // Console.WriteLine($"element clicked = {name}, type = {controlType}");
        // Console.WriteLine($"{args.RawEvent}, {args.Data.X}, {args.Data.Y}");
    }

    static string GetElementString(AutomationElement focusedElement)
    {
        string name = focusedElement?.Current.Name ?? "<unnamed element>";
        string controlType = focusedElement?.Current.ControlType?.ProgrammaticName ?? "<unknown type>";
        return ($"{controlType}(name = {name})");
    }
    static string GetElementPath(AutomationElement focusedElement)
    {
      AutomationElement currentElement = focusedElement;
      List<string> pathNodes = new List<string>();
      while (currentElement != null)
      {
        string currentString = GetElementString(currentElement);
        pathNodes.Add(currentString);
        currentElement = TreeWalker.ControlViewWalker.GetParent(currentElement);
      }

      pathNodes.Reverse();
      string path = String.Join(" > ", pathNodes.ToArray());
      return path;
    }
}
