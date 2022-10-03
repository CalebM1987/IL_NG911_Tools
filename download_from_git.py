#!/usr/bin/python
import os

destination_path  = os.path.dirname(__file__).replace(os.sep, '/')
clone_command = "git clone https://github.com/CalebM1987/IL_NG911_Tools.git" 

if os.path.basename(destination_path) != "IL_NG911_Tools":
    clone_with_path = clone_command  +" "+ destination_path + "/IL_NG911_Tools"
    os.system(clone_with_path)
