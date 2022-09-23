from ..support.munch import munchify

class STREET_BASE:
    PRE_MOD='St_PreMod' 
    PRE_DIRECTION='St_PreDir' 
    PRE_TYPE='St_PreTyp' 
    PRE_TYPE_SEPERATOR='St_PreSep' 
    NAME='St_Name' 
    POST_TYPE='St_PosTyp' 
    POST_DIRECTION='St_PosDir' 
    POST_MODIFIER='St_PosMod' 
    LEGACY_PRE_DIR='LSt_PreDir' 
    LEGACY_NAME='LSt_Name' 
    LEGACY_TYPE='LSt_Type' 
    LEGACY_POST_DIR='LSt_PosDir'

class STREET_FIELDS(STREET_BASE):
    GUID = 'RCL_NGUID'
    ADDRESS_PREFIX_LEFT='AdNumPre_L'
    ADDRESS_PREFIX_RIGHT='AdNumPre_R'
    FROM_ADDRESS_LEFT='FromAddr_L'
    FROM_ADDRESS_RIGHT='FromAddr_R'
    TO_ADDRESS_LEFT='ToAddr_L'
    TO_ADDRESS_RIGHT='ToAddr_R'
    PARITY_LEFT='Parity_L'
    PARITY_RIGHT='Parity_L'
    PRE_DIRECTION='St_PreDir'
    POST_DIRECTION='St_PosDir'

class ADDRESS_FIELDS(STREET_BASE):
    GUID = 'Site_NGUID'
    CODE='AddCode' 
    DATA_URI='AddDataURI' 
    NEIGHBORHOOD_COMMUNITY='Nbrhd_Comm' 
    NUMBER_PREFIX='AddNum_Pre' 
    NUMBER='Add_Number' 
    NUMBER_SUFFIX='AddNum_Suf' 
    ESN='ESN' 
    BUILDING='Building'
    FLOOR='Floor' 
    UNIT='Unit' 
    ROOM='Room' 
    SEAT='Seat' 
    ADDITIONAL_LOC_INFO='Addtl_Loc' 
    LANDMARK='LandmkName' 
    MILE_POST='Mile_Post' 
    TYPE='Place_Type' 
    PLACEMENT='Placement'

POINT_SIDE_MAPPING = [
    {
        'pt': 'MSAGComm', 
        'ln': 'MSAGComm'
    }, 
    {
        'pt': 'Inc_Muni',
        'ln': 'IncMuni'
    },
    {
        'pt': 'Uninc_Comm',
        'ln': 'UnincCom'
    },
    {
        'pt': 'ESN', 
        'ln': 'ESN', 
    },
    { 
        'pt': 'Nbrhd_Comm',
        'ln': 'NbrhdCom',
    },
    { 
        'pt': 'Post_Code',
        'ln': 'PostCode',
    },
    { 
        'pt': 'Post_Comm',
        'ln': 'PostComm',
    },
    { 
        'pt': 'AddCode',
        'ln': 'AddCode',
    },
]

# important fields
class FIELDS:
    STREET = STREET_FIELDS
    ADDRESS = ADDRESS_FIELDS
