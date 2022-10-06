from ..support.munch import munchify
# from decimal import Decimal
import datetime

INTEGER_FIELDS = [
    'SmallInteger',
    'Integer'
]

FLOAT_FIELDS = [
    'Single',
    'Double',
]

NUMERIC_FIELDS = INTEGER_FIELDS + FLOAT_FIELDS

TYPE_MAPPING = munchify(dict(
    String=str,
    Single=float,
    Double=float,
    SmallInteger=int,
    Integer=int,
    Date=datetime.datetime,
    OID=int
))

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
    COUNTRY_L='Country_L'
    COUNTRY_R='Country_R'
    STATE_L='State_L'
    STATE_R='State_R'
    COUNTY_L='County_L'
    COUNTY_R='County_R'
    ADD_CODE_L='AddCode_L'
    ADD_CODE_R='AddCode_R'
    ESN_L='ESN_L'
    ESN_R='ESN_R'
    MSAG_COM_L = 'MSAGComm_L'
    MSAG_COM_R = 'MSAGComm_R'
    INC_MUNI_L='IncMuni_L'
    INC_MUNI_R='IncMuni_R'
    UNINC_MUNI_L='UnincCom_L'
    UNINC_MUNI_R='UnincCom_R'
    NEIGHBORHOOD_COM_L='NbrhdCom_L'
    NEIGHBORHOOD_COM_R='NbrhdCom_R'
    POST_CODE_L='PostCode_L'
    POST_CODE_R='PostCode_R'
    POST_COM_L='PostComm_L'
    POST_COM_R='PostComm_R'
    ONE_WAY='OneWay'
    SPEED_LIMIT='SpeedLimit'
    VALID_L='Valid_L'
    VALID_R='Valid_R'
  

class ADDRESS_FIELDS(STREET_BASE):
    GUID = 'Site_NGUID'
    CODE='AddCode' 
    DATA_URI='AddDataURI' 
    NEIGHBORHOOD_COM='Nbrhd_Comm' 
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
    MSAG_COM='MSAGComm'
    POST_CODE='Post_Code'
    POST_CODE_4='Post_Code4'
    INC_MUNI='Inc_Muni'
    UNINC_MUNI='Uninc_Comm'
    NEIGHBORHOOD_COM='Nbrhd_Comm'
    COUNTRY='Country'
    STATE='State'
    COUNTY='County'

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
