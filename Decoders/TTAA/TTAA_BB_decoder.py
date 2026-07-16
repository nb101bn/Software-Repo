import unittest
import json

def getPreffixTTAA(symbol):
    if symbol == '99':
        return 'surface'
    elif symbol == '00':
        return '1000mb'
    elif symbol == '77':
        return 'tropopause'
    elif symbol == '92':
        return '925mb'
    elif symbol == '85':
        return '850mb'
    elif symbol == '70':
        return '700mb'
    elif symbol == '50':
        return '500mb'
    elif symbol == '40':
        return '400mb'
    elif symbol == '30':
        return '300mb'
    elif symbol == '25':
        return '250mb'
    elif symbol == '20':
        return '200mb'
    elif symbol == '15':
        return '150mb'
    elif symbol == '10':
        return '100mb'
    return 'unkn'

def decode(message):
    if message[0:4] == 'TTAA':
        print("Decoded TTAA message")
        TTAA = decodeTTAA(message[5:])
        return TTAA
    elif message[0:4] == 'TTBB':
        print("Decoded TTBB message")
        TTBB = decodeTTBB(message[5:])
        return TTBB
    else:
        print("Unknown message type")
        return None

def decodeTTAA(message):
    """
    Decodes a TTAA message and returns a dictionary of data.
    """
    data = message.split(' ')
    res = {}
    prefix = '--'
    for idx in range(len(data)):
        if idx == 0:
            res['dayOfMonth'] = int(data[idx][0:2]) - 50
            res['hour'] = data[idx][2:4]
            res['windUpTo'] = data[idx][4:] + '00mb'
        elif idx == 1:
            res['station'] = data[idx]
        else:
            if (idx - 2) % 3 == 0:
                prefix = getPreffixTTAA(data[idx][0:2])
                pressure_val = int(data[idx][2:4])
                pressure_prefix = '1' if pressure_val < 200 else ''
                res[prefix + 'Pressure'] = pressure_prefix + data[idx][2:4] + 'mb'
            elif (idx - 2) % 3 == 1:
                group = data[idx]
                if group.isnumeric() and len(group) == 5:
                    # Corrected Temperature Calculation
                    temp_digits = group[0:3]
                    temp_val = int(temp_digits)
                    temp_sign = -1 if temp_val % 10 % 2 == 1 else 1
                    temp_abs = int(temp_digits[0:2]) + (int(temp_digits[2]) / 10)
                    res[prefix + 'Temperature'] = round(temp_sign * temp_abs, 1)

                    # Corrected Dewpoint Depression Calculation
                    dew_depression_str = group[3:]
                    dew_depression_val = int(dew_depression_str)
                    if dew_depression_val >= 50:
                        res[prefix + 'DewpointDepression'] = dew_depression_val - 50
                    else:
                        res[prefix + 'DewpointDepression'] = dew_depression_val / 10

                    if prefix + 'Temperature' in res and prefix + 'DewpointDepression' in res:
                        res[prefix + 'Dewpoint'] = round(res[prefix + 'Temperature'] - res[prefix + 'DewpointDepression'], 2)
                else:
                    res[prefix + 'Temperature'] = '///'
                    res[prefix + 'DewpointDepression'] = '///'
                    res[prefix + 'Dewpoint'] = '///'
            elif (idx - 2) % 3 == 2:
                group = data[idx]
                if group.isnumeric():
                    direction_str = group[0:3]
                    speed_str = group[3:]
                    if len(group) == 5:
                        res[prefix + 'WindDirection'] = direction_str + '0'
                        res[prefix + 'WindSpeed'] = speed_str + 'kt'
                    elif len(group) == 4:
                        res[prefix + 'WindDirection'] = direction_str
                        res[prefix + 'WindSpeed'] = speed_str + 'kt'
                else:
                    res[prefix + 'WindDirection'] = '///'
                    res[prefix + 'WindSpeed'] = '///'
    print(res)
    return res

def decodeTTBB(message):
    data = message.split(' ')
    res = {}
    res["station"] = data[1]
    res["dayOfMonth"] = int(data[0][0:2]) - 50
    res["hour"] = data[0][2:4]
    
    level_prefix_counts = {}
    current_level_prefix = ""

    for idx in range(2, len(data)):
        group = data[idx]

        if idx == 2 and group[0:2] == '00':
            current_level_prefix = "surface"
            res[current_level_prefix + "_pressure"] = group[2:] + "mb"
        elif (idx - 2) % 2 == 0:  # Pressure Group
            if group.isnumeric():
                level_id = group[0:2]
                if level_id in ['11', '22', '33', '44', '55', '66', '77', '88', '99']:
                    count = level_prefix_counts.get(level_id, 0) + 1
                    level_prefix_counts[level_id] = count
                    current_level_prefix = f"significant_level_{level_id}_{count}"
                    res[current_level_prefix + "_pressure"] = group[2:] + 'mb'
                else:
                    current_level_prefix = f"significant_level_{level_id}"
                    res[current_level_prefix + "_pressure"] = group[2:] + 'mb'
            else:
                current_level_prefix = "significant_level_unknown"
                res[current_level_prefix + "_pressure"] = '///'
        elif (idx - 2) % 2 == 1:  # Temp/DP group
            temp_group = group
            if temp_group.isnumeric() and len(temp_group) == 5:
                # Corrected Temperature Calculation
                temp_digits = temp_group[0:3]
                temp_val = int(temp_digits)
                temp_sign = -1 if temp_val % 10 % 2 == 1 else 1
                temp_abs = int(temp_digits[0:2]) + (int(temp_digits[2]) / 10)
                res[current_level_prefix + "_temperature"] = round(temp_sign * temp_abs, 2)

                # Corrected Dewpoint Depression Calculation
                dew_depression_str = temp_group[3:]
                dew_depression_val = int(dew_depression_str)
                if dew_depression_val >= 50:
                    res[current_level_prefix + "_dewpoint_depression"] = (dew_depression_val - 50)
                else:
                    res[current_level_prefix + "_dewpoint_depression"] = dew_depression_val / 10

                if current_level_prefix + "_temperature" in res:
                    res[current_level_prefix + "_dewpoint"] = round(res[current_level_prefix + "_temperature"] - res[current_level_prefix + "_dewpoint_depression"], 2)
            else:
                res[current_level_prefix + "_temperature"] = '///'
                res[current_level_prefix + "_dewpoint_depression"] = '///'
                res[current_level_prefix + "_dewpoint"] = '///'

    print(res)
    return res

class TestDecodeTTAA(unittest.TestCase):
    def runTest(self):
        self.caseA()
        self.caseB()
    def testTTAA(self):
      TTAA = decode("TTAA 80121 72440 99973 24619 20001 00146 ///// ///// 92839 27057 19012 85580 20632 24509 70229 11067 23013 50595 06958 25011 40765 17165 22013 30975 30773 24516 25102 40376 25007 20250 52563 05012 15430 66158 19016 10672 68560 25511 88134 70556 21518 77999 31313 45408 81114 51515 10164 00055 10194 21510 22011=")
      TTBB = decode("TTBB 80128 72440 00973 24619 11960 28450 22930 27458 33916 26256 44808 16820 55795 17658 66788 17660 77770 15859 88738 12657 99726 12059 11721 11457 22711 11460 33705 11466 44696 11069 55685 10269 66677 09870 77655 08069 88638 06672 99593 02062 11578 00664 22574 00263 33567 00366 44563 00763 55560 00965 66545 02158 77542 02358 88534 03158 99511 05957 11485 07762 22482 08161 33475 08565 44469 09164 55466 09564 66459 10161 77436 12565 88430 13164 99426 13764 11412 15760 22395 17766 33386 19165 44374 20570 55357 23366 66346 25165 77328 26778 88295 31773 99279 34577 11252 39776 22242 41973 33224 46168 44210 49766 55208 50365 66184 56348 77165 61759 88162 62759 99156 64159 11134 70556 22132 70356 33129 69956 44125 70356 55121 70157 66118 70357 77109 68159 88107 68159 99104 68760 11100 68560 21212 00973 20001 11962 18512 22950 20012 33935 19513 44919 19010 55888 20511 66881 20012 77859 22509 88850 24509 99831 23513 11822 24012 22800 23511 33774 21512 44765 21512 55746 22012 66728 22510 77720 21511 88705 23012 99697 22514 11683 21510 22669 22007 33660 21007 44652 21508 55634 20009 66622 21509 77616 21506 88608 22008 99603 22506 11597 23507 22586 23007 33569 25006 44563 24505 55542 27008 66531 28011 77525 27511 88508 26510 99497 24512 11486 24510 22481 23510 33472 25009 44451 23513 55447 24012 66432 23014 77422 22511 88412 21013 99406 21012 11392 23013 22383 22514 33358 28012 44355 27513 55346 28012 66342 28513 77331 25516 88327 25015 99324 25518 11317 26017 22310 26015 33299 24516 44296 24015 55285 25011 66275 22509 77272 21009 88246 25507 99243 25007 11240 24507 22237 26007 33228 30001 44216 06007 55207 05010 66198 05513 77196 05512 88190 04509 99180 08009 11169 12011 22162 15008 33142 20021 44134 21518 55130 23020 66128 22022 77126 21521 88124 21518 99118 20520 11116 20518 22114 20517 33112 19521 44110 20022 55103 24010 66100 25511=")
      print(TTAA)
      print(TTBB)
      with open("TTAA_decoded.json", "w") as f:
          TTAA_json = json.dump(TTAA, f, indent=2)
      with open("TTBB_decoded.json", "w") as f:
        TTBB_json = json.dump(TTBB, f, indent=2)

def __main__():
  unittest.main()

if __name__ == "__main__":
  __main__()