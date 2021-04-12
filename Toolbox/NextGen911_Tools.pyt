# -*- coding: utf-8 -*-
import os
import sys
import arcpy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ilng911.env import ng911_db
from ilng911.geoprocessing import table_to_params


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [
            CreateRoadCenterline
        ]


class CreateRoadCenterline(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Road Centerline"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = table_to_params(ng911_db.roadCenterlines)
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return