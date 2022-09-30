{
    "schemas": [
        {
            "featureType": "ROAD_CENTERLINE",
            "fieldMap": [
              {
                    "name": "LeftFrom",
                    "expression": "{FromAddr_L}",
                    "type": "LONG"
                },
                {
                    "name": "LeftTo",
                    "expression": "{ToAddr_L}",
                    "type": "LONG"
                },
                {
                    "name": "RightFrom",
                    "expression": "{FromAddr_R}",
                    "type": "LONG"
                },
                {
                    "name": "RightTo",
                    "expression": "{ToAddr_R}",
                    "type": "LONG"
                },
                {
                    "name": "PreDirectional",
                    "expression": "{St_PreDir}",
                    "type": "TEXT",
                    "length": 2
                },
                {
                    "name": "PreType",
                    "expression": "{St_PreTyp}",
                    "type": "TEXT",
                    "length": 10
                },
                {
                    "name": "StreetName",
                    "expression": "{St_Name}",
                    "type": "TEXT",
                    "length": 100
                },
                {
                    "name": "PostType",
                    "expression": "{St_PosTyp}",
                    "type": "TEXT",
                    "length": 6
                },
                {
                    "name": "PostDirectional",
                    "expression": "{St_PosDir}",
                    "type": "TEXT",
                    "length": 2
                },
                {
                    "name": "LeftZipCode",
                    "expression": "{PostCode_L}",
                    "type": "TEXT",
                    "length": 10
                },
                {
                    "name": "RightZipCode",
                    "expression": "{PostCode_R}",
                    "type": "TEXT",
                    "length": 10
                },
                {
                    "name": "MPH",
                    "expression": "{SpeedLimit}",
                    "type": "SHORT"
                },
                {
                    "name": "LPostCity",
                    "expression": "{Post_Comm_L}",
                    "type": "TEXT",
                    "length": 32
                },
                {
                    "name": "RPostCity",
                    "expression": "{Post_Comm_R}",
                    "type": "TEXT",
                    "length": 32
                }
            ]
        },
        {
            "featureType": "ADDRESS_POINTS",
            "fieldMap": [
                {
                    "name": "HouseNumber",
                    "expression": "{Add_Number}",
                    "type": "TEXT",
                    "length": 10
                },
                {
                    "name": "HouseSuffix",
                    "expression": "{AddNum_Suf}",
                    "type": "TEXT",
                    "length": 32
                },
                {
                    "name": "PreDirectional",
                    "expression": "{St_PreDir}",
                    "type": "TEXT",
                    "length": 2
                },
                {
                    "name": "PreType",
                    "expression": "{St_PreTyp}",
                    "type": "TEXT",
                    "length": 10
                },
                {
                    "name": "StreetName",
                    "expression": "{St_Name}",
                    "type": "TEXT",
                    "length": 100
                },
                {
                    "name": "PostType",
                    "expression": "{St_PosTyp}",
                    "type": "TEXT",
                    "length": 6
                },
                {
                    "name": "PostDirectional",
                    "expression": "{St_PosDir}",
                    "type": "TEXT",
                    "length": 2
                },
                {
                    "name": "UNIT",
                    "expression": "{Unit}",
                    "type": "TEXT",
                    "length": 32
                },
                {
                    "name": "Zip",
                    "expression": "{Post_Code}",
                    "type": "TEXT",
                    "length": 20
                },
                {
                    "name": "PostalCity",
                    "expression": "{Post_Comm}",
                    "type": "TEXT",
                    "length": 32
                }
            ]
        }
    ]
}