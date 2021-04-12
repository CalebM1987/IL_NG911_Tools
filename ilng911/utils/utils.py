from ..env import py_info

needs_arc_message = False
if py_info.is_arc:
    import arcpy
    needs_arc_message = True


def message(*args):
    """prints one or more messages to the stdout.  If being used in an arcpy process, it will also call arcpy.AddMessage()"""
    for msg in args:
        print(str(msg))
        if needs_arc_message:
            arcpy.AddMessage(str(msg))