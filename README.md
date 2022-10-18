# ilng911 

This package contains NextGen 911 Tools for Illinois Counties. This has been designed to run in ArcGIS Pro and tools are provided through a [Python Toolbox](https://pro.arcgis.com/en/pro-app/2.8/arcpy/geoprocessing_and_python/a-quick-tour-of-python-toolboxes.htm).  

These tools assume there is a Geodatabase that conforms to the specific NextGen 911 schemas as outlined in the [required layers resource](./resources/NG911%20Required%20Data%20Layers_ltr.pdf):

![Required Layers GDB](/resources/images/reqLayersGDB.png)

Before these tools can get used, there is a preconfiguration step that needs to be set up by the 911 GIS Data Administrator. It is also **strongly recommended** to create a shared ArcGIS Pro Project that can be used to input new addresses.

## Installation

The recommended way to install these tools is by using [git](https://git-scm.com/downloads) to install from the [Github](https://github.com/CalebM1987/IL_NG911_Tools) repo. By using `git`, that will also make it easier to get the updated code for these tools when bugs are fixed or enhancements are added. Any bugs that get fixed or new features will be displayed in the [Changelog](./CHANGELOG.md).

Once you have `git` installed on your machine, the tools can be installed. **These tools should be installed on a shared network drive where the tools are accesible both to the end user who will perform address updates and the administrator**. run this command in the `bash` command propmpt: 

```sh
# cd to network shared folder, where it is accesible to all users
cd //your-server/GIS/ng911 

# once inside your shared network folder, clone the git repo
git clone git@github.com:CalebM1987/IL_NG911_Tools.git
```

This will install the tools in a folder called `IL_NG911_Tools` into whatever folder you ran the bash script from.

> Note: It is very important not to alter the folder structure of this package. **Moving any files around will likely break the tools**.


## Administrator Setup

The 911 GIS Data Administrator should follow the steps on the [Administrator Help Page](./Administrator.md) to set up the configuration database, ArcGIS Pro Document, and the Pro Tasks to streamline the 911 Tools.




