#!/usr/bin/python
import os

destination_path  = os.path.dirname(__file__).replace(os.sep, '/')
clone_command = "git clone https://github.com/CalebM1987/IL_NG911_Tools.git" 

if os.path.basename(destination_path) != "IL_NG911_Tools":
    full_path = destination_path + "/IL_NG911_Tools"

    # prevent potential "dubius ownership in repository" error
    trust_cmd = f"git config --global --add safe.directory '%(prefix)/{full_path}'"
    os.system(trust_cmd)

    # now clone to trusted safe.directory
    clone_with_path = f'{clone_command} {full_path}'
    os.system(clone_with_path)
