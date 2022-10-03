# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

## 1.1.0-alpha.0 (2022-10-03)


### Features

* added address validation tables ([1639ad6](https://github.com/CalebM1987/IL_NG911_Tools/commit/1639ad6dca1d7374424dbb92be014a60da5f086b))
* added nena guid field name to 911 tables ([43e11cc](https://github.com/CalebM1987/IL_NG911_Tools/commit/43e11cc51323a640161839cbecd6adf2b2b7226b))
* calculate vendor fields ([db15a75](https://github.com/CalebM1987/IL_NG911_Tools/commit/db15a75d89900dfe6be4e8536a5989e699b68e01))
* populate ng911 tables ([4d6cd05](https://github.com/CalebM1987/IL_NG911_Tools/commit/4d6cd05834e350e5ef8681f151f451cdd0c0ba19))
* track unique NENA identifiers ([e63bb91](https://github.com/CalebM1987/IL_NG911_Tools/commit/e63bb915356b8c4cbfbd964d27ee01cf84b36c7e))
* **addins:** added dev addins ([2d53d31](https://github.com/CalebM1987/IL_NG911_Tools/commit/2d53d31ba577b7fee6e9da488a3389115f50fe99))
* **address:** add attributes based on side/parity ([17658bf](https://github.com/CalebM1987/IL_NG911_Tools/commit/17658bf0776a7ebc70f001e29859bddec7832ad0))
* **admin:** create schemas geodatabase ([b234f2c](https://github.com/CalebM1987/IL_NG911_Tools/commit/b234f2ca5835885fc86c5c7ff59dbf440b435d6d))
* **core:** merge centerline attributes with address point ([e18e835](https://github.com/CalebM1987/IL_NG911_Tools/commit/e18e83552da80dc9933579bf4338d2f4428348e2))
* **core:** support custom calculated fields ([cf1ae98](https://github.com/CalebM1987/IL_NG911_Tools/commit/cf1ae987a8a90e4835660a0e116be3347939ee04))
* **core/address:** merge street attributes and location info ([0976865](https://github.com/CalebM1987/IL_NG911_Tools/commit/09768655db036cc969a14a33f75bc9a7b28f6163))
* **database:** added setup method ([3e8d421](https://github.com/CalebM1987/IL_NG911_Tools/commit/3e8d4213ef599c19cfb77f3c4d6aad1054733034))
* **database:** use singleton for NG911Data class ([2abc34e](https://github.com/CalebM1987/IL_NG911_Tools/commit/2abc34e55cb536f98803154a9986154d25f539f0))
* **helper_scripts:** initial schema helpers ([7c8bc8b](https://github.com/CalebM1987/IL_NG911_Tools/commit/7c8bc8b5f7784233ccab99398c3051de2faf81d5))
* **ilng911:** initial setup of ilng911 package ([6e94824](https://github.com/CalebM1987/IL_NG911_Tools/commit/6e9482494badbc8d719d514e02cecd12b6be8ef7))
* **schemas:** register NENA identifiers ([868e8a8](https://github.com/CalebM1987/IL_NG911_Tools/commit/868e8a857f5d7092e273652952559a13c9ed7ee3))
* use config file to find ng911 schemas ([65f5201](https://github.com/CalebM1987/IL_NG911_Tools/commit/65f5201eea863cdb188d1b526f1447c72553e0e8))


### Bug Fixes

* **psap:** fixed typo for PSAP identifier field ([20ba672](https://github.com/CalebM1987/IL_NG911_Tools/commit/20ba6727e2f17f67c8c65dae0ed5b06159c71678))
* fixed calculating field from expression ([4d304c2](https://github.com/CalebM1987/IL_NG911_Tools/commit/4d304c221079faa829fedcb2fdc46032d2b0c8a6)), closes [#2](https://github.com/CalebM1987/IL_NG911_Tools/issues/2)
* **common:** fixed missing Feature properties ([ef815db](https://github.com/CalebM1987/IL_NG911_Tools/commit/ef815dbcddbb35426f8d2c12c82871b53baa0b95))
* filter custom fields from parameters because they get autopopulated ([539984c](https://github.com/CalebM1987/IL_NG911_Tools/commit/539984c263b17e578b065ceb41370f08610166b2))
* remove circular imports ([6c40f69](https://github.com/CalebM1987/IL_NG911_Tools/commit/6c40f698eb639eea5b392fcf498adc21658f16d0))
