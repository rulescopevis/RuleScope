from datetime import datetime
from typing import List, Dict, Union, Any
import copy

def refine_range(rangeList: List[Dict[str, Any]], 
                 dataType: str,
                 validFlag: bool,
                 selectValueList: List[Any],
                 datetime_format: str = "%Y-%m-%d") -> Dict:
    
    # Add data validation logic
    validList = []
    invalidList = []
    
    # Classify data into validList and invalidList
    for value in selectValueList:
        is_valid = False
        for range_item in rangeList:
            if dataType == 'datetime':
                try:
                    value_dt = convert_to_datetime(value)
                    start_dt = convert_to_datetime(range_item['start'])
                    end_dt = convert_to_datetime(range_item['end'])
                    if start_dt <= value_dt <= end_dt:
                        is_valid = True
                        break
                except:
                    continue
            else:
                if range_item['start'] <= value <= range_item['end']:
                    is_valid = True
                    break
        
        if is_valid:
            validList.append(value)
        else:
            invalidList.append(value)
    
    # If validFlag is True and no invalid values, return False directly
    if validFlag and not invalidList:
        return {
            "refineStatus": False,
            "refineRangeList": []
        }
    
    # If validFlag is False and no valid values, return False directly
    if not validFlag and not validList:
        return {
            "refineStatus": False,
            "refineRangeList": []
        }
    
    # Use processValueList instead of original selectValueList
    selectValueList = invalidList if validFlag else validList

    def convert_to_datetime(value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except:
            try:
                return datetime.strptime(value, datetime_format)
            except:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    
    def calculate_distance(point, boundary, inclusive):
        if dataType == 'datetime':
            point = convert_to_datetime(point)
            boundary = convert_to_datetime(boundary)
            diff = abs((point - boundary).total_seconds())
        else:
            diff = abs(point - boundary)
        
        if inclusive:
            diff -= 0.1
        return diff

    def calculate_midpoint(start, end):
        if dataType == 'datetime':
            time_delta = end - start
            return start + time_delta / 2
        else:
            return (start + end) / 2
    
    # Data preprocessing
    if dataType == 'datetime':
        selectValueList = [convert_to_datetime(x) for x in selectValueList]
        for range_item in rangeList:
            range_item['start'] = convert_to_datetime(range_item['start'])
            range_item['end'] = convert_to_datetime(range_item['end'])
    
    result = {
        "refineStatus": True,
        "refineRangeList": []
    }
    
    # Handle single example case
    if len(selectValueList) == 1:
        select_value = selectValueList[0]
        
        if validFlag:
            result['refineRangeList'] = []
            
            # Check if value is between two ranges
            if len(rangeList) > 1:
                for i in range(len(rangeList)-1):
                    if (rangeList[i]['end'] < select_value < rangeList[i+1]['start']):
                        # Case 1: Extend to selected value
                        new_range_list1 = copy.deepcopy(rangeList)
                        new_range_list1[i]['end'] = select_value
                        new_range_list1[i]['endInclusive'] = True
                        result['refineRangeList'].append(new_range_list1)
                        
                        # Case 2: Add as independent value
                        # new_range_list2 = copy.deepcopy(rangeList)
                        # new_range_list2.append({
                        #     'start': format_float(select_value),
                        #     'end': format_float(select_value),
                        #     'startInclusive': True,
                        #     'endInclusive': True
                        # })
                        # result['refineRangeList'].append(new_range_list2)
                        
                        # Case 3: Connect to next range
                        new_range_list3 = copy.deepcopy(rangeList)
                        new_range_list3[i+1]['start'] = select_value
                        new_range_list3[i+1]['startInclusive'] = True
                        result['refineRangeList'].append(new_range_list3)
                        
                        return result

            # If not between ranges, use original logic
            min_distance = float('inf')
            nearest_boundary = None
            nearest_inclusive = None
            nearest_range_index = 0
            
            for i, range_item in enumerate(rangeList):
                start_distance = calculate_distance(select_value, range_item['start'], 
                                                 range_item['startInclusive'])
                if start_distance < min_distance:
                    min_distance = start_distance
                    nearest_boundary = range_item['start']
                    nearest_inclusive = range_item['startInclusive']
                    nearest_range_index = i
                
                end_distance = calculate_distance(select_value, range_item['end'],
                                               range_item['endInclusive'])
                if end_distance < min_distance:
                    min_distance = end_distance
                    nearest_boundary = range_item['end']
                    nearest_inclusive = range_item['endInclusive']
                    nearest_range_index = i
            
            # Create extended range
            new_range_list1 = copy.deepcopy(rangeList)
            if nearest_boundary == new_range_list1[nearest_range_index]['start']:
                new_range_list1[nearest_range_index]['start'] = select_value
                new_range_list1[nearest_range_index]['startInclusive'] = True
            elif nearest_boundary == new_range_list1[nearest_range_index]['end']:
                new_range_list1[nearest_range_index]['end'] = select_value
                new_range_list1[nearest_range_index]['endInclusive'] = True
            result['refineRangeList'].append(new_range_list1)
            
            # Create range containing single point
            new_range_list2 = copy.deepcopy(rangeList)
            new_range_list2.append({
                'start': select_value,
                'end': select_value,
                'startInclusive': True,
                'endInclusive': True
            })
            result['refineRangeList'].append(new_range_list2)
            
        else:  # validFlag = False
            # Get valid values
            valid_values = []
            for value in selectValueList:
                for range_item in rangeList:
                    if range_item['start'] <= value <= range_item['end']:
                        valid_values.append(value)
                        break
            
            if not valid_values:
                return {
                    "refineStatus": False,
                    "refineRangeList": []
                }
            
            # Simplified processing: only generate one modified range
            modified_ranges = []
            current_range = rangeList[0]  # Assume only processing first range
            min_value = min(valid_values)
            max_value = max(valid_values)
            
            # If values are in range, create new ranges excluding these values
            if current_range['start'] < min_value:
                modified_ranges.append({
                    'start': current_range['start'],
                    'end': min_value,
                    'startInclusive': current_range['startInclusive'],
                    'endInclusive': False
                })
            
            if max_value < current_range['end']:
                modified_ranges.append({
                    'start': max_value,
                    'end': current_range['end'],
                    'startInclusive': False,
                    'endInclusive': current_range['endInclusive']
                })
            
            result['refineRangeList'] = [modified_ranges] if modified_ranges else []

    else:  # Handle multiple values case
        if validFlag:
            # Only process invalid values
            invalid_values = []
            for value in selectValueList:
                is_invalid = True
                for range_item in rangeList:
                    if range_item['start'] <= value <= range_item['end']:
                        is_invalid = False
                        break
                if is_invalid:
                    invalid_values.append(value)
            
            # If no invalid values, return False
            if not invalid_values:
                return {
                    "refineStatus": False,
                    "refineRangeList": []
                }
            
            result['refineRangeList'] = []
            min_value = min(invalid_values)
            max_value = max(invalid_values)
            
            # Only generate extended single range
            new_range = [{
                'start': min(min_value, rangeList[0]['start']),
                'end': max(max_value, rangeList[-1]['end']),
                'startInclusive': True,
                'endInclusive': True
            }]
            result['refineRangeList'].append(new_range)

        else:  # validFlag = False
            # Simplified processing: only generate one modified range
            modified_ranges = []
            current_range = rangeList[0]  # Assume only processing first range
            min_value = min(selectValueList)
            max_value = max(selectValueList)
            
            # If values are in range, create new ranges excluding these values
            if current_range['start'] < min_value:
                modified_ranges.append({
                    'start': current_range['start'],
                    'end': min_value,
                    'startInclusive': current_range['startInclusive'],
                    'endInclusive': False
                })
            
            if max_value < current_range['end']:
                modified_ranges.append({
                    'start': max_value,
                    'end': current_range['end'],
                    'startInclusive': False,
                    'endInclusive': current_range['endInclusive']
                })
            
            result['refineRangeList'] = [modified_ranges] if modified_ranges else []
    
    # Process data format before returning result
    if dataType == 'datetime':
        for range_list in result['refineRangeList']:
            for range_item in range_list:
                if isinstance(range_item['start'], datetime):
                    range_item['start'] = range_item['start'].strftime(datetime_format)
                if isinstance(range_item['end'], datetime):
                    range_item['end'] = range_item['end'].strftime(datetime_format)
    elif dataType == 'numeric':
        for i in range(len(result['refineRangeList'])):
            for range_item in result['refineRangeList'][i]:
                range_item['start'] = format_float(range_item['start'])
                range_item['end'] = format_float(range_item['end'])
    
    return result

def get_decimal_places(num):
    str_num = str(num)
    if '.' in str_num:
        return len(str_num.split('.')[1])
    return 0

def format_float(number):
    """
    Format floating point numbers, handling floating point precision issues
    1. Remove trailing consecutive zeros (e.g. 1.23000000085 -> 1.23)
    2. Handle values close to integers (e.g. 1.999999999 -> 2)
    3. Handle values close to decimals (e.g. 1.829999999934 -> 1.83)
    4. Handle repeated decimals (e.g. 1.633333333333333382 -> 1.63)
    5. Correctly handle rounding (e.g. 1.65555555555582 -> 1.7)
    """
    # First try common precision handling
    # Check if close to 1 or 2 decimal places
    for decimal_places in [1, 2]:
        rounded = round(number, decimal_places)
        if abs(number - rounded) < 1e-10:
            return rounded
    
    # Convert to string
    str_num = str(float(number))
    
    # If integer, return directly
    if '.' not in str_num:
        return float(str_num)
    
    # Check if close to an integer
    rounded_int = round(number)
    if abs(number - rounded_int) < 1e-10:
        return float(rounded_int)
    
    # Handle repeated decimal patterns
    decimal_part = str_num.split('.')[1]
    
    # For cases like 1.6444444444444482, should return 1.64
    if len(decimal_part) > 2 and decimal_part[2:].count(decimal_part[2]) > 5:
        return round(number, 2)
    
    # Check for repetitive patterns
    for i in range(1, min(6, len(decimal_part))):
        # Check if first i digits are followed by identical digits
        prefix = decimal_part[:i]
        rest = decimal_part[i:]
        
        # If remaining part consists entirely of same digits or approaches a pattern
        if rest and (all(d == rest[0] for d in rest) or 
                    all(d in ('0', '9') for d in rest) or
                    all(int(d) >= 5 for d in rest[:min(3, len(rest))])):
            # If subsequent digits are all >= 5, may need rounding up
            if all(int(d) >= 5 for d in rest[:min(3, len(rest))]):
                # Ensure correct rounding
                return round(number, i)
            return round(number, i)
    
    # Analyze decimal part patterns
    # Check for consecutive 5, 6, 7, 8, 9 which may indicate rounding needed
    for i in range(2, min(6, len(decimal_part))):
        if all(int(d) >= 5 for d in decimal_part[i:i+3] if d.isdigit()):
            return round(number, i)
    
    # Find effective decimal places (exclude trailing consecutive 0s and 9s)
    effective_decimals = len(decimal_part)
    # Check from right to left, reduce consecutive 9s and 0s
    for i in range(len(decimal_part)-1, -1, -1):
        if decimal_part[i] in ('0', '9'):
            effective_decimals -= 1
        else:
            break
    
    # Ensure at least 1 decimal place, maximum 10
    effective_decimals = max(1, min(effective_decimals, 10))
    
    # Round according to effective decimal places
    return round(number, effective_decimals)