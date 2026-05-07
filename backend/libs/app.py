import math
import os
import re
import shutil
import sys
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))  
backend_root = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_root)
sys.path.append(current_dir)
sys.path.append(backend_root)
sys.path.append(project_root)

import atexit
from flask import Flask, request, jsonify, make_response, send_file
from flask_cors import CORS
import copy
from rule_implementer.detect_mapping_and_cardinality import *
from rule_implementer.detect_duplicate_multiple import *
from rule_refiner.refine_NL import refine_NL
from nl_panel_intent import detect_nl_intent
from locate_rule import locate_rule_type_and_columns, extract_rule_from_validation
from generate_original_rule import *
from update_rules import update_validation_rules
from rule_refiner.refine_main import *
from rule_implementer.detect_difference_multiple import *
from rule_generator.cell_level.type import *
from rule_generator.cell_level.character_info import *
from rule_generator.cell_level.numeric_info import *
from rule_generator.cell_level.date_info import *
from rule_implementer.detect_duplicate import * 
from rule_implementer.detect_sequence import *
from rule_implementer.detect_condition_logic import *
from json_parser import *
from rule_implementer.detect_format import *
from rule_implementer.detect_difference import *
from rule_implementer.detect_computation import *
from rule_implementer.detect_range import *
from rule_implementer.detect_compare_numeric import *
from rule_implementer.detect_compare_date import *
from rule_implementer.detect_statistical import *
from rule_implementer.detect_normal_value import *
from rule_implementer.detect_compare_substring import *
from rule_generator.dependency_level.extract_invalid_range import *
from rule_implementer.detect_conflict_flag import detect_conflict_flag
from generate_card_example import *
from constraintMapGenerator import generate_constraint_map
from detection_script_builder import build_detection_script
from main import generate_validation_rule
from llms import get_api_config, save_api_config
import pandas as pd
import json
import time
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:8080"}})

# Current dataset selection, None means no dataset chosen yet
current_dataset = None

# Global path placeholders
csv_file_path = None
json_file_path = None
new_json_file_path = None
vis_json_path = None
table_json_path = None
tableVisInfo_json_path = None
constraint_map_json_path = None
dataset_path = None
data_path = os.path.join(backend_root, "dataset")
workflow_mode = "ollama"
UPLOAD_PREFIX = "upload::"
UPLOAD_ROOT = os.path.join(backend_root, "uploadFile")
DATASET_ROOT = os.path.join(backend_root, "dataset")

# Remove temporary validation and constraint files inside dataset/upload roots
def clear_temp_files():
    for root_dir in [DATASET_ROOT, UPLOAD_ROOT]:
        if not root_dir or not os.path.exists(root_dir):
            continue
        for root, _, files in os.walk(root_dir):
            for file in files:
                if (
                    file.startswith("validation_rules_") and file.endswith(".json")
                ) or (
                    file.startswith("constraintMap_") and file.endswith(".json")
                ):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except OSError as exc:
                        print(f"Failed to delete temp file {file_path}: {exc}")

# Configure file paths based on the currently selected dataset
def set_dataset_paths():
    global csv_file_path, json_file_path, new_json_file_path, vis_json_path, table_json_path, tableVisInfo_json_path, constraint_map_json_path, dataset_path, timestamp

    if dataset_path != None:
        # Delete temp files from previous dataset selection
        temp_files = [new_json_file_path, constraint_map_json_path]
        for temp_file in temp_files:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
    timestamp = int(math.floor(time.time()))
    
    if current_dataset == "basketball":
        # Basketball dataset path
        dataset_path = os.path.join(DATASET_ROOT, "basketball") + os.sep
        csv_file_path = dataset_path + "test-data.csv"
    elif current_dataset == "electrocar1":
        # Electrocar dataset path
        dataset_path = os.path.join(DATASET_ROOT, "electrocar") + os.sep
        csv_file_path = dataset_path + "test-data.csv"
    elif current_dataset == "animal":
        # Animal dataset path
        dataset_path = os.path.join(DATASET_ROOT, "animal") + os.sep
        csv_file_path = dataset_path + "test-data.csv"
    elif current_dataset:
        dataset_key = current_dataset
        if dataset_key.startswith(UPLOAD_PREFIX):
            dataset_key = dataset_key[len(UPLOAD_PREFIX):]
        custom_dataset_path = os.path.join(UPLOAD_ROOT, dataset_key)
        if os.path.isdir(custom_dataset_path):
            dataset_path = custom_dataset_path + os.sep
            csv_file_path = dataset_path + "test-data.csv"
        else:
            dataset_path = None
            csv_file_path = None
            json_file_path = None
            new_json_file_path = None
            vis_json_path = None
            table_json_path = None
            tableVisInfo_json_path = None
            constraint_map_json_path = None
            print(f"Dataset not found: {current_dataset}")
            return
    else:
        csv_file_path = None
        json_file_path = None
        new_json_file_path = None
        vis_json_path = None
        table_json_path = None
        tableVisInfo_json_path = None
        constraint_map_json_path = None
    
    if dataset_path:
        json_file_path = dataset_path + "validation_rules.json"
        new_json_file_path = dataset_path + f"validation_rules_{timestamp}.json"
        with open(new_json_file_path, 'w', encoding='utf-8') as file:
            json_data = json.load(open(json_file_path, 'r', encoding='utf-8'))
            json.dump(json_data, file, ensure_ascii=False, indent=4)
        vis_json_path = dataset_path + "visInfo.json"
        table_json_path = dataset_path + "table_info.json"
        tableVisInfo_json_path = dataset_path + "tableVisInfo.json"
        constraint_map_json_path = dataset_path + f"constraintMap_{timestamp}.json"
        generate_constraint_map(new_json_file_path, csv_file_path, constraint_map_json_path)


def set_workflow_mode(mode: str):
    global workflow_mode
    workflow_mode = "api" if mode == "api" else "ollama"
    return workflow_mode


def get_model_from_workflow():
    return None if workflow_mode == "ollama" else "api"


def sanitize_dataset_name(filename: str) -> str:
    base_name = os.path.splitext(os.path.basename(filename or ""))[0]
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", base_name).strip("_")
    if not sanitized:
        sanitized = f"uploaded_{int(time.time())}"
    return sanitized


def regenerate_constraint_map():
    """Rebuild the constraint map after rules change."""
    global new_json_file_path, csv_file_path, constraint_map_json_path
    if not (
        new_json_file_path
        and csv_file_path
        and constraint_map_json_path
        and os.path.exists(new_json_file_path)
        and os.path.exists(csv_file_path)
    ):
        return
    try:
        generate_constraint_map(
            new_json_file_path,
            csv_file_path,
            constraint_map_json_path,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to regenerate constraint map: {exc}")

def _normalize_refine_result_for_frontend(refine_result: dict) -> dict:
    """Massage refine_NL output to match frontend expectations.

    - Ensure refineResultStatus mirrors refineStatus.
    - For Range rules, flatten rangeList into refineRule as a list of ranges.
    - Add example strings when missing so RefineModel can render checkboxes.
    - Guarantee optional fields exist to avoid KeyErrors in UI.
    """

    if not isinstance(refine_result, dict):
        return refine_result

    refine_result = dict(refine_result)
    refine_status = refine_result.get("refineStatus")
    refine_result.setdefault("refineResultStatus", refine_status)

    refine_dict = refine_result.get("refineDict") or {}
    if not isinstance(refine_dict, dict):
        return refine_result

    refine_result.setdefault("refineResultStatus", refine_result.get("refineStatus"))

    def normalize_rules(rules, add_example_defaults: bool = False):
        normalized = []
        for rule in rules or []:
            if not isinstance(rule, dict):
                normalized.append(rule)
                continue

            rule = dict(rule)
            col_val = rule.get("column")
            if isinstance(col_val, list) and len(col_val) == 1:
                rule["column"] = col_val[0]

            # Range: move rangeList -> refineRule[0]
            refine_rule = rule.get("refineRule")
            if (
                isinstance(refine_rule, dict)
                and rule.get("type") == "Range"
                and "rangeList" in refine_rule
            ):
                rule["refineRule"] = [refine_rule.get("rangeList", [])]

            if add_example_defaults:
                rule.setdefault("original_example", rule.get("original_example", ""))
                rule.setdefault("refine_example", rule.get("refine_example", ""))
            normalized.append(rule)
        return normalized

    # First structural normalize (without adding empty example placeholders)
    refine_dict["addRules"] = normalize_rules(refine_dict.get("addRules", []), add_example_defaults=False)
    refine_dict["updateRules"] = normalize_rules(refine_dict.get("updateRules", []), add_example_defaults=False)
    refine_dict["deleteRules"] = normalize_rules(refine_dict.get("deleteRules", []), add_example_defaults=False)

    # Generate human-readable examples if they are missing (RefineModel expects them)
    def _has_examples(rule_list):
        return any(
            isinstance(rule, dict)
            and (
                (isinstance(rule.get("original_example"), str) and rule.get("original_example").strip())
                or (isinstance(rule.get("refine_example"), str) and rule.get("refine_example").strip())
            )
            for rule in (rule_list or [])
        )

    try:
        if not any(_has_examples(refine_dict.get(k)) for k in ("addRules", "updateRules", "deleteRules")):
            enriched = generate_example(copy.deepcopy({"refineDict": refine_dict}))
            if isinstance(enriched, dict) and isinstance(enriched.get("refineDict"), dict):
                refine_dict = enriched["refineDict"]
    except Exception as exc:  # noqa: BLE001
        print(f"[normalize_refine] generate_example failed: {exc}")

    # Re-normalize after enrichment and add example defaults for UI safety
    refine_dict["addRules"] = normalize_rules(refine_dict.get("addRules", []), add_example_defaults=True)
    refine_dict["updateRules"] = normalize_rules(refine_dict.get("updateRules", []), add_example_defaults=True)
    refine_dict["deleteRules"] = normalize_rules(refine_dict.get("deleteRules", []), add_example_defaults=True)

    # Flatten single-column columnsList in rule_context if present
    rc = refine_result.get("ruleContext")
    if isinstance(rc, dict):
        cols = rc.get("columnsList")
        if isinstance(cols, list) and len(cols) == 1:
            rc["columnsList"] = cols[0]
        refine_result["ruleContext"] = rc
    refine_result["refineDict"] = refine_dict
    return refine_result
# Initialize paths and clear temporary files
clear_temp_files()
set_dataset_paths()
atexit.register(clear_temp_files)

@app.route('/api/change-dataset', methods=['POST'])
def api_change_dataset():
    try:
        global current_dataset
        data = request.get_json()
        dataset = data.get('dataset')
        mode = data.get('workflowMode')
        if mode:
            set_workflow_mode(mode)
        
        # if dataset not in ["basketball", "electrocar", "football", "electrocar-processed"]:
        #     return jsonify({'error': 'invalid dataset name'}), 400
            
        clear_temp_files()
        current_dataset = dataset
        set_dataset_paths()
        if not dataset_path:
            return jsonify({'error': f'dataset {dataset} not found'}), 404
        
        return jsonify({'message': f'{dataset} has been selected', 'workflowMode': workflow_mode}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflow-mode', methods=['POST'])
def api_workflow_mode():
    try:
        data = request.get_json()
        mode = data.get('workflowMode')
        if mode not in ('ollama', 'api'):
            return jsonify({'error': 'Invalid workflow mode'}), 400
        updated_mode = set_workflow_mode(mode)
        return jsonify({'workflowMode': updated_mode}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/api-config', methods=['GET'])
def api_get_api_config():
    try:
        return jsonify(get_api_config()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/api-config', methods=['POST'])
def api_save_api_config():
    try:
        data = request.get_json() or {}
        saved_config = save_api_config(data)
        return jsonify(saved_config), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-dataset', methods=['POST'])
def api_upload_dataset():
    try:
        global current_dataset
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'error': 'Invalid file'}), 400

        workflow_mode_form = request.form.get('workflowMode')
        if workflow_mode_form:
            set_workflow_mode(workflow_mode_form)

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'Only .csv files are supported at the moment'}), 400

        dataset_name = sanitize_dataset_name(file.filename)
        os.makedirs(UPLOAD_ROOT, exist_ok=True)
        dataset_dir = os.path.join(UPLOAD_ROOT, dataset_name)
        if os.path.exists(dataset_dir):
            shutil.rmtree(dataset_dir)
        os.makedirs(dataset_dir, exist_ok=True)

        dataset_csv_path = os.path.join(dataset_dir, 'test-data.csv')
        file.save(dataset_csv_path)

        df = pd.read_csv(dataset_csv_path)
        model_param = get_model_from_workflow()
        generate_validation_rule(df, dataset_name, model_param, dataset_dir, orderConditionDict={})

        validation_rules_path = os.path.join(dataset_dir, 'validation_rules.json')
        final_validation_path = os.path.join(dataset_dir, 'finalValidation.json')
        shutil.copyfile(validation_rules_path, final_validation_path)

        clear_temp_files()
        current_dataset = f"{UPLOAD_PREFIX}{dataset_name}"
        set_dataset_paths()

        return jsonify({
            'message': 'Dataset uploaded successfully',
            'dataset': current_dataset,
            'displayName': dataset_name
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect_lookup', methods=['POST'])
def api_detect_lookup():
    try:
        data = request.get_json()
        columnNames = data.get('columnNames', [])
        lookup_list = load_lookup_list(new_json_file_path, columnNames)
        df = pd.read_csv(csv_file_path)
        df.replace([None, ''], np.nan, inplace=True)
        invalid_indices = detect_lookup(df[columnNames[0]], df[columnNames[1]], lookup_list)
        return jsonify({'invalid_indices': invalid_indices})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/load_table_vis_valueList', methods=['POST'])
def api_load_table_vis_valueList():
    try:

        data = request.get_json()
        column_name = data.get('column_name', "")
 
        valueList = load_column_data(tableVisInfo_json_path, column_name)
        return jsonify({'valueList': valueList})
    except KeyError:
        return jsonify({"error": f"Column '{column_name}' not found in JSON data"}), 404

@app.route('/api/load_column_data', methods=['POST'])
def api_load_column_data():
    try:
        data = request.get_json()
        column_name = data.get('column_name', "")

        valueList = load_column_data(vis_json_path, column_name)
        return jsonify({'valueList': valueList})
    except KeyError:
        return jsonify({"error": f"Column '{column_name}' not found in JSON data"}), 404

@app.route('/api/load_missing_duplicate_detect_flag', methods=['POST'])
def api_load_missing_duplicate_detect_flag():
    try:
        data = request.get_json()
        column_name = data.get('column_name', "")

        missing_detect_flag, duplicate_detect_flag = load_missing_duplicate_detect_flag(new_json_file_path, column_name)
        return jsonify({'missing_detect_flag': missing_detect_flag, 'duplicate_detect_flag': duplicate_detect_flag})
    except KeyError:
        return jsonify({"error": f"Column '{column_name}' not found in JSON data"}), 404

@app.route('/api/load_missing_duplicate_flag', methods=['POST'])
def api_load_missing_duplicate_flag():
    try:
        data = request.get_json()
        column_name = data.get('column_name', "")

        missing_flag, duplicate_flag = load_missing_duplicate_flag(new_json_file_path, column_name)
        return jsonify({'missing_flag': missing_flag, 'duplicate_flag': duplicate_flag})
    except KeyError:
        return jsonify({"error": f"Column '{column_name}' not found in JSON data"}), 404

@app.route('/api/detect_column_types', methods=['POST'])
def api_detect_column_types():
    try:
        data = request.get_json()
        df = pd.DataFrame(data['csvData'])
        result = detect_column_types(df)
        return jsonify(result)
    except Exception as e:
        return jsonify({'result': False, 'error': str(e)}), 400

# Return character missing indices
@app.route('/api/character_missing', methods=['POST'])
def api_character_missing():
    try:
        # Read request payload
        data = request.get_json()
        column_name = data.get("columnName")  # Column name

        special_missing_values = load_special_missing_values(new_json_file_path, column_name)
        df_column = pd.read_csv(csv_file_path)[column_name]
        df_column.replace([None, ''], np.nan, inplace=True)
        result = character_missing(df_column, special_missing_values = special_missing_values)
        missing_dict = result.get('missingDict', {})

        all_index = list(missing_dict.get('index', []))
        if 'specialMissingList' in missing_dict:
            all_index += [idx for item in missing_dict['specialMissingList'] for idx in item.get('index', [])]

        return jsonify({'missingIndices': all_index})
    except Exception as e:
        return jsonify({'error': str(e)}), 501

@app.route('/api/character_duplicate', methods=['POST'])
def api_character_duplicate():
    try:
        data = request.get_json()
        if 'column_data' not in data:
            return jsonify({'error': 'Missing column_data field'}), 400
        
        column_data = data['column_data']
        df_column = pd.Series(column_data)
        result = character_duplicate(df_column)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 502

# Detect indices that do not match a given regex pattern
@app.route('/api/detect_format', methods=['POST'])
def api_detect_format():
    try:
        # Read request payload
        data = request.get_json()

        # Extract column data and regex pattern
        column_data = data['selectedcolumn']
        format = data['format']

        # Convert column data to pandas Series
        column = pd.Series(column_data)

        # Run detect_format
        result = detect_format(column, format)

        # Return response
        return jsonify({'indices': result}), 200
    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400

@app.route('/api/detect_substring_character', methods=['POST'])
def api_detect_substring_character():
    try:
        # Read request payload
        data = request.get_json()
        selectedColumns = data["selectedColumns"]

        # Parse column data
        column1_data = data[selectedColumns[0]]
        column2_data = data[selectedColumns[1]]
        
        # Convert to pandas Series
        column1 = pd.Series(column1_data)
        column2 = pd.Series(column2_data)
        
        # Run detect_substring_character
        invalid_indices = detect_substring_character([column1, column2])

        # Return response
        return jsonify({'invalid_indices': invalid_indices})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/numeric_order_duplicate', methods=['POST'])
def api_numeric_order_duplicate():
    try:
        data = request.get_json()
        if 'column_data' not in data:
            return jsonify({'error': 'Missing column_data field'}), 400
        
        column_data = data['column_data']
        df_column = pd.Series(column_data)
        result = numeric_order_duplicate(df_column)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 601
    
# Return duplicate value indices across charts
@app.route('/api/detect_duplicate', methods=['POST'])
def api_detect_duplicate():
    try:
        data = request.get_json()
        if 'column_data' not in data:
            return jsonify({'error': 'Missing column_data field'}), 400
        
        column_data = data['column_data']
        df_column = pd.Series(column_data)
        result = detect_duplicate(df_column)
        return jsonify({'duplicateIndices': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 602

# Return numeric missing indices
@app.route('/api/numeric_missing', methods=['POST'])
def api_numeric_missing():
    try:
        # Receive column name from frontend
        data = request.get_json()
        column_name = data.get("columnName")  # Column name
        special_missing_values = load_special_missing_values(new_json_file_path, column_name)
        df_column = pd.read_csv(csv_file_path)[column_name]
        df_column.replace([None, ''], np.nan, inplace=True)
        result = numeric_missing(df_column, numeric_missing_values = special_missing_values)
        missing_dict = result.get('missingDict', {})
        all_index = list(missing_dict.get('index', []))
        return jsonify({'missingIndices': all_index})
    except Exception as e:
        return jsonify({'error': str(e)}), 603

@app.route('/api/detect_absolute_difference', methods=['POST'])
def api_detect_absolute_difference():
    try:
        # Read request payload
        data = request.get_json()
        column_name = data.get('column_name', "")

        df = pd.read_csv(csv_file_path)
        # Replace common missing value markers with NaN
        df.replace([None, ''], np.nan, inplace=True)

        orderCondition = load_order_condition_json(new_json_file_path, column_name)
        differenceThreshold = load_absolute_difference_json(new_json_file_path, column_name)
        # Load table info for column metadata
        with open(table_json_path, 'r', encoding='utf-8') as file:
            table_dict = json.load(file)

        # Run absolute difference detection
        invalid_pairs = detect_absolute_difference(df, column_name, orderCondition, differenceThreshold, table_dict)

        # Return response
        return jsonify({'invalid_pairs': invalid_pairs}), 200
    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400

@app.route('/api/detect_relative_difference', methods=['POST'])
def api_detect_relative_difference():
    try:
        # Read request payload
        data = request.get_json()
        column_name = data.get('column_name', "")

        df = pd.read_csv(csv_file_path)
        # Replace common missing value markers with NaN
        df.replace([None, ''], np.nan, inplace=True)

        orderCondition = load_order_condition_json(new_json_file_path, column_name)
        differenceThreshold = load_relative_difference_json(new_json_file_path, column_name)
        # Load table info for column metadata
        with open(table_json_path, 'r', encoding='utf-8') as file:
            table_dict = json.load(file)

        # Run relative difference detection
        invalid_pairs = detect_relative_difference(df, column_name, orderCondition, differenceThreshold, table_dict)

        # Return response
        return jsonify({'invalid_pairs': invalid_pairs}), 200
    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400

@app.route('/api/detect_multi_difference', methods=['POST'])
def api_detect_multi_difference():
    try:
        data = request.get_json()
        column_names = data.get('columnNames', [])

        df = pd.read_csv(csv_file_path)
        df.replace([None, ''], np.nan, inplace=True)
        
        difference = load_multi_difference_json(new_json_file_path, column_names)
        orderCondition = load_multi_difference_order_condition_json(new_json_file_path, column_names)

        # Load table info for column metadata
        with open(table_json_path, 'r', encoding='utf-8') as file:
            table_dict = json.load(file)
        # Run multi-column difference detection
        invalid_pairs = detect_multi_difference(df, column_names, orderCondition, difference, table_dict)

        return jsonify({'invalid_pairs': invalid_pairs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/detect_formula_numeric', methods=['POST'])
def api_detect_formula_numeric():
    try:
        # Read request payload
        data = request.get_json()

        # When selectedColumns and operationList are provided
        selectedColumns = data['selectedColumns']
        variable_list = []

        column_data_1 = pd.Series(selectedColumns[0])
        variable_list.append(column_data_1)
        column_data_2 = pd.Series(selectedColumns[1])
        variable_list.append(column_data_2)
        operation_data = data['operationList']

        # Run detect_formula_numeric
        result = detect_formula_numeric(variable_list, operation_data)

        # Return response
        return jsonify({'invalid_indices': result}), 200
    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400

# For numeric charts, only start/end are needed; indices are not required
@app.route('/api/detect_numeric_range', methods=['POST'])
def api_detect_numeric_range():
    try:
        # Read request payload
        data = request.get_json()

        # Extract column data and range rules
        selectedColumn = data['selectedColumn']
        df = pd.read_csv(csv_file_path)

        df.replace([None, ''], np.nan, inplace=True)
        column_data = df[selectedColumn]
        range_rule = load_range_rule_json(new_json_file_path, selectedColumn)
        result = detect_numeric_range(column_data, range_rule)

        return jsonify({'invalid_indices': result}), 200
    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400

# Return numeric range start and end
@app.route('/api/json_numeric_range', methods=['POST'])
def api_json_numeric_range():
    try:
        # Read request payload
        data = request.get_json()

        # Extract column data and range rules
        column_name = data['selectedColumn']
        rule_type = data.get('ruleType', 'Range')

        if rule_type == 'Outlier':
            range_rule = load_outlier_rule_json(new_json_file_path, column_name)
            start = range_rule.get('start') if range_rule else None
            end = range_rule.get('end') if range_rule else None
        else:
            range_rule_list = load_range_rule_json(new_json_file_path, column_name)
            first_rule = range_rule_list[0] if range_rule_list else {}
            start = first_rule.get('start')
            end = first_rule.get('end')

        # Return extracted range data
        return jsonify({
            'start': start,
            'end': end
        }), 200

    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400

@app.route('/api/detect_outliers', methods=['POST'])
def api_detect_outliers():
    try:
       # Read request payload
        data = request.get_json()

        # Extract column data and outlier rule
        selectedColumn = data['selectedColumn']
        df = pd.read_csv(csv_file_path)
        df.replace([None, ''], np.nan, inplace=True)
        column_data = df[selectedColumn]
        range_rule = load_outlier_rule_json(new_json_file_path, selectedColumn)
        result = detect_numeric_range(column_data, [range_rule])

        return jsonify({'invalid_indices': result}), 200
    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/detect_compare_numeric', methods=['POST'])
def api_detect_compare_numeric():
    try:
        # Read request payload
        data = request.get_json()
        
        # Extract requested columns
        csv_data = pd.read_csv(csv_file_path)
        selectedColumns = data['selectedColumns']

        compare_type = load_compare_numeric(new_json_file_path, selectedColumns)

        # Convert csvData to pandas DataFrame
        df = pd.DataFrame(csv_data)
        # Replace common missing value markers with NaN
        df.replace([None, ''], np.nan, inplace=True)

        # Extract the two columns for comparison
        column1 = df[selectedColumns[0]]
        column2 = df[selectedColumns[1]]

        # Run compare_numeric detection
        invalid_indices = detect_compare_numeric([column1, column2], compare_type)
        
        # Respond with invalid indices
        return jsonify({
            'invalid_indices': invalid_indices,
        }), 200
    
    except Exception as e:
        # Error handling
        return jsonify({
            'error': str(e)
        }), 400

@app.route('/api/detect_compare_numeric_valid', methods=['POST'])
def api_detect_compare_numeric_valid():
    try:
        # Read request payload
        data = request.get_json()

        # Extract requested columns and data
        csv_data = data['csvData']
        selectedColumns = data['selectedColumns']
        json_path = new_json_file_path
        compare_type = load_compare_numeric(json_path, selectedColumns)
        if not compare_type:
            return jsonify({'error': 'compare rule not found'}), 404
        if len(selectedColumns) != 2:
            return jsonify({'error': 'selectedColumns must include two columns'}), 400
        
        # Convert csvData to pandas DataFrame
        df = pd.DataFrame(csv_data)
        # Replace common missing value markers with NaN
        df.replace([None, ''], np.nan, inplace=True)
        # Extract columns to compare
        column1 = df[selectedColumns[0]]
        column2 = df[selectedColumns[1]]
        
        # Run detect_compare_numeric to get invalid indices
        invalid_indices = detect_compare_numeric([column1, column2], compare_type)

        # All row indices
        all_indices = set(range(len(csv_data)))

        # Derive valid indices via complement
        valid_indices = sorted(list(all_indices - set(invalid_indices)))

        # Return valid indices
        return jsonify({
            'valid_indices': valid_indices
        }), 200
    
    except Exception as e:
        # Error handling
        return jsonify({'error': str(e)}), 400


@app.route('/api/detect_compare_date', methods=['POST'])
def api_detect_compare_date():
    try:
        data = request.get_json()
        selectedColumns = data['selectedColumns']

        if not selectedColumns or len(selectedColumns) != 2:
            return jsonify({'error': 'selectedColumns must include two columns'}), 400

        compare_info = load_compare_date(new_json_file_path, selectedColumns)
        if not compare_info:
            return jsonify({'error': 'compare rule not found'}), 404

        compare_type = compare_info.get('compareRelation')
        column_formats = compare_info.get('columnFormats', [])

        df = pd.read_csv(csv_file_path)
        df.replace([None, ''], np.nan, inplace=True)

        column1 = df[selectedColumns[0]]
        column2 = df[selectedColumns[1]]

        invalid_indices = detect_compare_date(
            [column1, column2], compare_type, column_formats
        )

        return jsonify({'invalid_indices': invalid_indices}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/detect_compare_date_valid', methods=['POST'])
def api_detect_compare_date_valid():
    try:
        data = request.get_json()
        csv_data = data['csvData']
        selectedColumns = data['selectedColumns']

        if not selectedColumns or len(selectedColumns) != 2:
            return jsonify({'error': 'selectedColumns must include two columns'}), 400

        compare_info = load_compare_date(new_json_file_path, selectedColumns)
        if not compare_info:
            return jsonify({'error': 'compare rule not found'}), 404

        compare_type = compare_info.get('compareRelation')
        column_formats = compare_info.get('columnFormats', [])

        df = pd.DataFrame(csv_data)
        df.replace([None, ''], np.nan, inplace=True)

        column1 = df[selectedColumns[0]]
        column2 = df[selectedColumns[1]]

        invalid_indices = detect_compare_date(
            [column1, column2], compare_type, column_formats
        )
        all_indices = set(range(len(csv_data)))
        valid_indices = sorted(list(all_indices - set(invalid_indices)))

        return jsonify({'valid_indices': valid_indices}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/detect_normal_value', methods=['POST'])
def api_detect_normal_value():
    try:
        # Read request payload
        data = request.get_json()

        # Parse column data
        column_data = data['selectedColumn']
        value_list = data['valueList']
        
        # Convert column data to pandas Series
        column = pd.Series(column_data)
        
        # Run detect_normal_value
        value_indices = detect_normal_value(column, value_list)

        # Return response
        return jsonify({'value_indices': value_indices})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

# Analyze datetime column data
@app.route('/api/analyze_date_column', methods=['POST'])
def api_analyze_date_column():
    try:
        data = request.get_json()
        column_data = data.get('column_data', [])
        
        if not column_data:
            return jsonify({'error': 'No data provided'}), 400

        series = pd.Series(column_data)
        result = analyze_date_column(series)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 700

# Matrix endpoint
# case3: return indices that violate sequence rules
@app.route('/api/detect_sequence', methods=['POST'])
def api_detect_sequence():
    try:
        data = request.get_json()
        column_name = data.get('column_name', "")
        df = pd.read_csv(csv_file_path)
        # Replace common missing value markers with NaN
        df.replace([None, ''], np.nan, inplace=True)
        orderCondition = load_order_condition_json(new_json_file_path, column_name)
        sequence_rule = load_sequence_rule_json(new_json_file_path, column_name)
        # Load table info for column metadata
        with open(table_json_path, 'r', encoding='utf-8') as file:
            table_dict = json.load(file)

        invalid_pairs = detect_sequence(df, column_name, orderCondition, sequence_rule, table_dict)
        return jsonify({'invalid_pairs': invalid_pairs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 800

# Return valid sequence pairs
@app.route('/api/detect_sequence_valid', methods=['POST'])
def api_detect_sequence_valid():
    try:
        data = request.get_json()
        column_name = data.get('column_name', "")
        df = pd.read_csv(csv_file_path)
        # Replace common missing value markers with NaN
        df.replace([None, ''], np.nan, inplace=True)
        orderCondition = load_order_condition_json(new_json_file_path, column_name)
        sequence_rule = load_sequence_rule_json(new_json_file_path, column_name)
        # Load table info for column metadata
        with open(table_json_path, 'r', encoding='utf-8') as file:
            table_dict = json.load(file)

        valid_pairs = detect_sequence_valid_pairs(df, column_name, orderCondition, sequence_rule, table_dict)
  
        return jsonify({'valid_pairs': valid_pairs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 800

# case2: return indices that violate inter-column validation rules
@app.route('/api/detect_condition_logic_index', methods=['POST'])
def api_detect_condition_logic_index():
    # Receive payload
    data = request.json
    csv_data = data.get('csvData')
    selectedColumns = data.get('selectedColumns')
    # Validate input
    if not csv_data or not selectedColumns:
        return jsonify({"error": "Invalid input"}), 400

    # Convert CSV data to DataFrame
    dataframe = pd.DataFrame(csv_data)
    # Replace common missing value markers with NaN
    dataframe.replace([None, ''], np.nan, inplace=True)

    # Load JSON file and parse conditions/constraints
    condition_json_file = new_json_file_path
    conditions_constraints = load_condition_logic_json(condition_json_file, selectedColumns)

    # Validate that conditions/constraints exist
    if not conditions_constraints:
        return jsonify({"error": "No matching conditions found in JSON"}), 404

    # Run optimized detect_logic_condition
    try:
        # Pass conditions_constraints directly
        invalid_indices = detect_logic_condition_mod(dataframe, conditions_constraints)
    except Exception as e:
        # Capture errors and return message
        return jsonify({"error": f"Error during detection: {str(e)}"}), 500

    # Return detected invalid indices
    return jsonify({"invalid_indices": sorted(list(invalid_indices))})

# case2: return indices for valid data
@app.route('/api/detect_condition_logic_index_valid', methods=['POST'])
def api_detect_condition_logic_index_valid():
    # Receive payload
    data = request.json
    csv_data = data.get('csvData')
    selected_columns = data.get('selectedColumns')

    if not csv_data or not selected_columns or len(selected_columns) != 2:
        return jsonify({"error": "Invalid input"}), 400

    # Reuse existing endpoint to get invalid indices
    response = api_detect_condition_logic_index()

    # Extract invalid indices
    invalid_indices = response.json.get("invalid_indices", [])
    
    # Calculate valid indices (complement)
    all_indices = set(range(len(csv_data)))
    valid_indices = sorted(list(all_indices - set(invalid_indices)))

    # Return valid indices
    return jsonify({"valid_indices": valid_indices})

@app.route('/api/extract_invalid_range', methods=['POST'])
def api_extract_invalid_range():
    # Receive payload
    data = request.json
    csv_data = data.get('csvData')
    selectedColumns = data.get('selectedColumns')
    # Validate input
    if not csv_data or not selectedColumns or len(selectedColumns) != 2:
        return jsonify({"error": "Invalid input"}), 400

    # Convert CSV data to DataFrame
    dataframe = pd.DataFrame(csv_data)
    # Replace common missing value markers with NaN
    dataframe.replace([None, ''], np.nan, inplace=True)

    # Load JSON and parse conditions/constraints
    condition_json_file = new_json_file_path
    conditions_constraints = load_condition_logic_json(condition_json_file, selectedColumns)

    # Extract start/end ranges for conditions
    result = extract_invalid_range(conditions_constraints)
    # Return extracted result
    return jsonify(result)

@app.route('/api/extract_lookup_area', methods=['POST'])
def api_extract_lookup_area():
    try:
        # Read request payload
        data = request.get_json()
        column_names = data.get('columnNames', [])
        
        # Validate input parameters
        if not column_names or len(column_names) != 2:
            return jsonify({"error": "Invalid column names"}), 400
            
        # Extract lookup area definitions
        lookup_areas = extract_lookup_area(new_json_file_path, column_names)
        return jsonify({"lookup_areas": lookup_areas}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sequence_invalid_range', methods=['POST'])
def api_sequence_invalid_range():
    data = request.get_json()
    column_name = data.get('column_name')
    sequence_rule = load_sequence_rule_json(new_json_file_path, column_name)
    invalid_range = sequence_invalid_range(sequence_rule)
    return jsonify({'invalid_range': invalid_range})

@app.route('/api/update-rule', methods=['POST'])
def update_rule():
    # Update rule from settings panel
    data = request.get_json()
    
    # Extract parameters
    column_name = data.get('columnName')  # First column name
    rule_type = data.get('ruleType')
    rule_value = data.get('ruleValue')
    # Validate input parameters
    if not column_name or not rule_type:
        return jsonify({"error": "Invalid input"}), 400
    
    # Read existing JSON file
    if not os.path.exists(new_json_file_path):
        return jsonify({"error": "File not found"}), 404
    
    try:
        with open(new_json_file_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
        
        # Ensure column exists
        if column_name[0] not in json_data:
            return jsonify({"error": f"Column {column_name} not found"}), 400

        # Update values based on rule type
        if rule_type == 'Missing':
            df = pd.read_csv(csv_file_path)
            json_data[column_name[0]]["missingDetectFlag"] = rule_value["missingDetectFlag"]
            json_data[column_name[0]]["specialMissingValueList"] = rule_value["specialMissingValueList"]
            # Update missingValueFlag
            # Step 1: detect standard missing values
            has_standard_missing = df[column_name[0]].isnull().any() or df[column_name[0]].isna().any()
            if has_standard_missing:
                json_data[column_name[0]]["missingValueFlag"] = True
            if not has_standard_missing:
                special_missing_values = rule_value["specialMissingValueList"]
                # Check for any special missing values in dataframe
                has_special_missing = df[column_name[0]].isin(special_missing_values).any()
                if has_special_missing:
                    json_data[column_name[0]]["missingValueFlag"] = True
                else:
                    json_data[column_name[0]]["missingValueFlag"] = False
        elif rule_type == 'Duplicate':
            json_data[column_name[0]]["duplicateDetectFlag"] = rule_value["duplicateDetectFlag"]
        elif rule_type == 'Type':
            json_data[column_name[0]]["columnType"] = rule_value
        elif rule_type == 'Difference':
            # Update difference rule
            json_data[column_name[0]]["difference"]["difference"]["start"] = rule_value["start"]
            json_data[column_name[0]]["difference"]["difference"]["end"] = rule_value["end"]
            json_data[column_name[0]]["difference"]["difference"]["startInclusive"] = rule_value["startInclusive"]
            json_data[column_name[0]]["difference"]["difference"]["endInclusive"] = rule_value["endInclusive"]
        elif rule_type == 'relativeDifference':
            # Update relativeDifference rule
            json_data[column_name[0]]["difference"]["relativeDifference"]["start"] = rule_value["start"]
            json_data[column_name[0]]["difference"]["relativeDifference"]["end"] = rule_value["end"]
            json_data[column_name[0]]["difference"]["relativeDifference"]["startInclusive"] = rule_value["startInclusive"]
            json_data[column_name[0]]["difference"]["relativeDifference"]["endInclusive"] = rule_value["endInclusive"]
        elif rule_type == 'Range':
            # Update range rule
            json_data[column_name[0]]["range"][0]["start"] = rule_value["start"]
            json_data[column_name[0]]["range"][0]["end"] = rule_value["end"]
            json_data[column_name[0]]["range"][0]["startInclusive"] = rule_value["startInclusive"]
            json_data[column_name[0]]["range"][0]["endInclusive"] = rule_value["endInclusive"]
        elif rule_type == 'Compare':
            if len(column_name) < 2:
                return jsonify({"error": "Compare rule requires two columns"}), 400

            # Determine whether comparison is date or numeric
            column_types = [
                json_data.get(column_name[0], {}).get("type"),
                json_data.get(column_name[1], {}).get("type"),
            ]
            is_date_compare = all(col_type == "datetime" for col_type in column_types)
            list_key = "dateCompareList" if is_date_compare else "numericCompareList"

            if list_key not in json_data:
                json_data[list_key] = []

            compare_relation = (
                rule_value.get("compareRelation")
                if isinstance(rule_value, dict)
                else rule_value
            )
            if compare_relation is None:
                return jsonify({"error": "Invalid compare relation"}), 400

            target_list = json_data[list_key]
            found = False
            for compare_rule in target_list:
                same_order = (
                    compare_rule.get("column1") == column_name[0]
                    and compare_rule.get("column2") == column_name[1]
                )
                reverse_order = (
                    compare_rule.get("column1") == column_name[1]
                    and compare_rule.get("column2") == column_name[0]
                )
                if same_order or reverse_order:
                    compare_rule["compareRelation"] = compare_relation
                    found = True
                    break

            if not found:
                target_list.append(
                    {
                        "column1": column_name[0],
                        "column2": column_name[1],
                        "compareRelation": compare_relation,
                    }
                )
        elif rule_type == 'Sequence':
            # Update sequence rules
            # Update matching rule if present
            for i, rule in enumerate(json_data[column_name[0]]["sequenceRule"]):
                if rule["value"] == rule_value["value"]:
                    json_data[column_name[0]]["sequenceRule"][i]["allowed_next"] = rule_value["allowed_next"]
                    break
            else:
                # Append new rule if no match
                json_data[column_name[0]]["sequenceRule"].append({
                    "value": rule_value["value"],
                    "allowed_next": rule_value["allowed_next"]
                })
        elif rule_type == 'Logical and condition':
            # Update logical-and condition rules
            found = False
            for condition_logic in json_data.get("conditionLogicColumnList", []):
                # Ensure column names match
                if (condition_logic.get("conditionColumns")[0] == column_name[0] and 
                    condition_logic.get("constraintColumns")[0] == column_name[1]):
                    
                    # Traverse condition/logic list
                    for condition_and_logic in condition_logic.get("conditionAndLogicList", []):
                        # Check condition column value match
                        condition_column_values = condition_and_logic.get("conditionColumnValue", [])
                        if condition_column_values and condition_column_values[0].get(column_name[0]) == [rule_value.get("conditionValue")]:
                            # Update constraint value
                            constraint_column_values = condition_and_logic.get("constraintColumnValue", [])
                            if not constraint_column_values:
                                constraint_column_values.append({})
                            constraint_column_values[0][column_name[1]] = rule_value["constraintValue"]
                            
                            found = True
                            break
                    
                    # Create a new condition when no match is found
                    if not found:
                        new_condition = {
                            "conditionColumnValue": [
                                {
                                    column_name[0]: [rule_value.get("conditionValue")]
                                }
                            ],
                            "constraintColumnValue": [
                                {
                                    column_name[1]: rule_value.get("constraintValue")
                                }
                            ]
                        }
                        condition_logic["conditionAndLogicList"].append(new_condition)
                        found = True
                    break
            
            if not found:
                return jsonify({"error": "No matching condition logic rule found"}), 404

        elif rule_type == 'Lookup':
            # Update Lookup rules
            # Ensure lookupList exists
            if "lookupList" not in json_data:
                json_data["lookupList"] = []

            # Find existing lookup rules for the column pair
            found = False
            for i, lookup_rule in enumerate(json_data["lookupList"]):
                if (lookup_rule["parentColumnName"] == column_name[0] and 
                    lookup_rule["childColumnName"] == column_name[1]):
                    # Iterate through new rules
                    for new_rule in rule_value["lookupList"]:
                        # Look for matching parent value rule
                        parent_found = False
                        for j, existing_rule in enumerate(lookup_rule["lookupList"]):
                            if existing_rule["parentValue"] == new_rule["parentValue"]:
                                # Update existing rule
                                json_data["lookupList"][i]["lookupList"][j]["childValueList"] = new_rule["childValueList"]
                                parent_found = True
                                break
                        
                        # Add new rule when no parent value matches
                        if not parent_found:
                            lookup_rule["lookupList"].append({
                                "parentValue": new_rule["parentValue"],
                                "childValueList": new_rule["childValueList"]
                            })
                    found = True
                    break
            
            # Add new column pair rule if none matched
            if not found:
                new_lookup_rule = {
                    "parentColumnName": column_name[0],
                    "childColumnName": column_name[1],
                    "lookupList": rule_value["lookupList"]
                }
                json_data["lookupList"].append(new_lookup_rule)

        # Persist changes to file
        with open(new_json_file_path, 'w', encoding='utf-8') as file:
            json.dump(json_data, file, ensure_ascii=False, indent=2)
        regenerate_constraint_map()
        
        return jsonify({"message": "Rule updated successfully"}), 200

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Print full traceback for debugging
        return jsonify({"error": f"Error updating rule: {str(e)}"}), 500

@app.route('/api/create-rule', methods=['POST'])
def create_rule():
    try:
        data = request.get_json()
        rule_type = data.get('type')
        columns = data.get('columns')
        parameters = data.get('parameters')

        if not rule_type or not columns:
            return jsonify({"error": "Missing required fields"}), 400

        if not os.path.exists(new_json_file_path):
            return jsonify({"error": "File not found"}), 404

        with open(new_json_file_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        col = columns[0]
        
        if rule_type == 'Type':
            if col in json_data:
                json_data[col]['type'] = parameters['type']
        
        elif rule_type == 'Format':
            if col in json_data:
                json_data[col]['format'] = parameters['format']

        elif rule_type == 'Integrity':
            if col in json_data:
                json_data[col]['missingDetectFlag'] = parameters['integrity_missingDetect']
                json_data[col]['specialMissingValueList'] = parameters['integrity_specialMissing']
                
                # Recalculate missingValueFlag
                df = pd.read_csv(csv_file_path)
                has_standard_missing = df[col].isnull().any() or df[col].isna().any()
                special_missing_values = parameters['integrity_specialMissing']
                has_special_missing = df[col].isin(special_missing_values).any()
                
                json_data[col]['missingValueFlag'] = bool(has_standard_missing or has_special_missing)

        elif rule_type == 'Range':
            if col in json_data:
                new_range = {
                    "start": float(parameters['range_min']) if parameters['range_min'] else None,
                    "end": float(parameters['range_max']) if parameters['range_max'] else None,
                    "startInclusive": parameters['range_min_op'] == '<=',
                    "endInclusive": parameters['range_max_op'] == '<='
                }
                json_data[col]['range'] = [new_range]

        elif rule_type == 'Domain consistency (same entity)':
            if col in json_data:
                json_data[col]['sameEntityList'] = parameters['domain_sameEntity']

        elif rule_type == 'Domain consistency (different domain)':
            if col in json_data:
                json_data[col]['differentDomainList'] = parameters['domain_differentDomain']

        elif rule_type == 'Outlier':
            if col in json_data:
                json_data[col]['outlierRange'] = {
                    "start": float(parameters['outlier_min']) if parameters['outlier_min'] else None,
                    "end": float(parameters['outlier_max']) if parameters['outlier_max'] else None,
                    "startInclusive": parameters['outlier_min_op'] == '<=',
                    "endInclusive": parameters['outlier_max_op'] == '<='
                }

        elif rule_type == 'Difference':
            if len(columns) > 1:
                if "multiDifference" not in json_data:
                    json_data["multiDifference"] = []
                
                new_rule = {
                    "columns": columns,
                    "differenceDict": {
                        "start": float(parameters['difference_min']) if parameters['difference_min'] else None,
                        "end": float(parameters['difference_max']) if parameters['difference_max'] else None,
                        "startInclusive": parameters['difference_min_op'] == '<=',
                        "endInclusive": parameters['difference_max_op'] == '<='
                    }
                }
                
                if parameters.get('orderCondition'):
                    order_cond = parameters['orderCondition']
                    date_cols = []
                    for key in ['firstOrderColumn', 'secondOrderColumn', 'thirdOrderColumn']:
                        ord_col = order_cond.get(key)
                        if ord_col and ord_col in json_data and json_data[ord_col].get('type') == 'date':
                            date_cols.append(ord_col)
                    order_cond['dateColumns'] = date_cols
                    new_rule['orderCondition'] = order_cond
                
                json_data["multiDifference"].append(new_rule)

            elif col in json_data:
                if "difference" not in json_data[col]:
                    json_data[col]["difference"] = {}
                
                json_data[col]["difference"]["difference"] = {
                    "start": float(parameters['difference_min']) if parameters['difference_min'] else None,
                    "end": float(parameters['difference_max']) if parameters['difference_max'] else None,
                    "startInclusive": parameters['difference_min_op'] == '<=',
                    "endInclusive": parameters['difference_max_op'] == '<='
                }
                
                if parameters.get('orderCondition'):
                    order_cond = parameters['orderCondition']
                    date_cols = []
                    for key in ['firstOrderColumn', 'secondOrderColumn', 'thirdOrderColumn']:
                        ord_col = order_cond.get(key)
                        if ord_col and ord_col in json_data and json_data[ord_col].get('type') == 'date':
                            date_cols.append(ord_col)
                    order_cond['dateColumns'] = date_cols
                    json_data[col]['orderCondition'] = order_cond

        elif rule_type == 'Duplicate':
            if len(columns) > 1:
                if "multipleDuplicateColumnsList" not in json_data:
                    json_data["multipleDuplicateColumnsList"] = []
                
                # Check if columns list is already in the list to avoid duplicates
                if columns not in json_data["multipleDuplicateColumnsList"]:
                    json_data["multipleDuplicateColumnsList"].append(columns)

            elif col in json_data:
                json_data[col]['duplicateDetectFlag'] = parameters['duplicate_detect']
                
                # Recalculate duplicateFlag
                df = pd.read_csv(csv_file_path)
                has_duplicates = df[col].duplicated().any()
                json_data[col]['duplicateFlag'] = bool(has_duplicates)

        elif rule_type == 'Comparison relation (compare)':
            if "numericCompareList" not in json_data:
                json_data["numericCompareList"] = []
            
            op_map = {
                "<": "smaller",
                ">": "larger",
                "<=": "smaller_equal",
                ">=": "larger_equal",
                "=": "equal"
            }
            op_symbol = parameters['compare_operator']
            relation = op_map.get(op_symbol, op_symbol)

            new_rule = {
                "column1": columns[0],
                "column2": columns[1],
                "compareRelation": relation
            }
            json_data["numericCompareList"].append(new_rule)

        elif rule_type == 'Comparison relation (substring)':
            if "substringList" not in json_data:
                json_data["substringList"] = []
            
            sub_col = parameters['substring_column']
            parent_col = columns[0] if columns[1] == sub_col else columns[1]
            
            new_rule = {
                "childColumn": sub_col,
                "parentColumn": parent_col
            }
            json_data["substringList"].append(new_rule)

        elif rule_type == 'Computational relation':
            if "formulaList" not in json_data:
                json_data["formulaList"] = []
            
            import re
            formula = parameters['computational_relation']
            operation_list = re.findall(r'[+\-*/=]', formula)
            
            new_rule = {
                "variableList": columns,
                "operationList": operation_list
            }
            json_data["formulaList"].append(new_rule)

        elif rule_type == 'Logical and condition':
            if "conditionLogicColumnList" not in json_data:
                json_data["conditionLogicColumnList"] = []
            
            lc_params = parameters['logical_and_condition']
            is_multi = len(columns) > 2
            target_list_key = "multipleConditionLogicColumnList" if is_multi else "conditionLogicColumnList"
            
            if target_list_key not in json_data:
                json_data[target_list_key] = []

            new_rule_entry = {
                "conditionColumns": lc_params['conditionColumns'],
                "constraintColumns": lc_params['constraintColumns'],
                "columnType": {},
                "conditionAndLogicList": []
            }
            
            for c in columns:
                ctype = json_data.get(c, {}).get('type', 'character')
                if ctype in ['numeric', 'date']:
                    new_rule_entry["columnType"][c] = "RangeBased"
                else:
                    new_rule_entry["columnType"][c] = "EqualityBased"

            # Aggregate across relations: merge constraints for identical condition combos
            merged_logic = {}

            def _variant_key(variant: dict) -> tuple:
                # Sort by column name to get stable key; stringify values
                return tuple(sorted((col, json.dumps(val, ensure_ascii=False)) for col, val in variant.items()))

            for rel in lc_params['relations']:
                # Build condition variants (cartesian product if multiple condition values)
                condition_variants = [dict()]
                for c in lc_params['conditionColumns']:
                    if c not in rel:
                        continue
                    val = rel[c]
                    col_type = new_rule_entry["columnType"].get(c, "EqualityBased")
                    if col_type == "RangeBased":
                        entry_val = {
                            "start": float(val['min']) if val['min'] else None,
                            "end": float(val['max']) if val['max'] else None,
                            "startInclusive": val['min_op'] == '<=',
                            "endInclusive": val['max_op'] == '<='
                        }
                        condition_variants = [
                            {**variant, c: entry_val} for variant in condition_variants
                        ]
                    else:
                        values = val.get('value') or []
                        if not isinstance(values, list):
                            values = [values]
                        new_variants = []
                        for variant in condition_variants:
                            for single_val in values:
                                new_variants.append({**variant, c: [single_val]})
                        condition_variants = new_variants or condition_variants

                # Build constraints (kept together; no expansion, later merged per variant)
                cons_list = []
                for c in lc_params['constraintColumns']:
                    if c in rel:
                        val = rel[c]
                        entry = {}
                        if new_rule_entry["columnType"][c] == "RangeBased":
                            entry[c] = {
                                "start": float(val['min']) if val['min'] else None,
                                "end": float(val['max']) if val['max'] else None,
                                "startInclusive": val['min_op'] == '<=',
                                "endInclusive": val['max_op'] == '<='
                            }
                        else:
                            cons_values = val.get('value') or []
                            if not isinstance(cons_values, list):
                                cons_values = [cons_values]
                            entry[c] = cons_values
                        cons_list.append(entry)

                for variant in condition_variants:
                    key = _variant_key(variant)
                    if key not in merged_logic:
                        merged_logic[key] = {
                            "conditions": variant,
                            "constraints": {}
                        }

                    target_constraints = merged_logic[key]["constraints"]
                    for cons_entry in cons_list:
                        for cons_col, cons_val in cons_entry.items():
                            col_type = new_rule_entry["columnType"].get(cons_col, "EqualityBased")
                            if col_type == "RangeBased":
                                # Range types: last one wins (cannot merge ranges safely)
                                target_constraints[cons_col] = cons_val
                            else:
                                existing = target_constraints.get(cons_col, [])
                                merged_vals = list(dict.fromkeys(existing + cons_val))
                                target_constraints[cons_col] = merged_vals

            # Emit merged conditionAndLogicList
            for entry in merged_logic.values():
                cond_list = [{k: v} for k, v in entry["conditions"].items()]
                cons_list = [{k: v} for k, v in entry["constraints"].items()]
                new_rule_entry["conditionAndLogicList"].append({
                    "conditionColumnValue": cond_list,
                    "constraintColumnValue": cons_list
                })

            json_data[target_list_key].append(new_rule_entry)

        elif rule_type == 'Mapping and cardinality':
            if "lookupList" not in json_data:
                json_data["lookupList"] = []
            
            parent_col = columns[0]
            child_col = columns[1]
            
            lookup_items = []
            for pair in parameters['mapping_cardinality']:
                p_vals = pair.get(parent_col, [])
                c_vals = pair.get(child_col, [])
                
                for p_val in p_vals:
                    lookup_items.append({
                        "parentValue": p_val,
                        "childValueList": c_vals
                    })
            
            new_rule = {
                "parentColumnName": parent_col,
                "childColumnName": child_col,
                "lookupList": lookup_items
            }
            json_data["lookupList"].append(new_rule)

        elif rule_type == 'Sequence':
            if col in json_data:
                seq_rules = []
                for item in parameters['sequence']:
                    seq_rules.append({
                        "value": item['currentValue'],
                        "allowed_next": item['nextValues']
                    })
                json_data[col]['sequenceRule'] = seq_rules
                
                if parameters.get('orderCondition'):
                    order_cond = parameters['orderCondition']
                    date_cols = []
                    for key in ['firstOrderColumn', 'secondOrderColumn', 'thirdOrderColumn']:
                        ord_col = order_cond.get(key)
                        if ord_col and ord_col in json_data and json_data[ord_col].get('type') == 'date':
                            date_cols.append(ord_col)
                    order_cond['dateColumns'] = date_cols
                    json_data[col]['orderCondition'] = order_cond

        with open(new_json_file_path, 'w', encoding='utf-8') as file:
            json.dump(json_data, file, ensure_ascii=False, indent=4)
        regenerate_constraint_map()

        return jsonify({"message": "Rule created successfully"}), 200

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # Print full traceback for debugging
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_constraint_map', methods=['GET'])
def api_get_constraint_map():
    # Ensure file exists
    if not os.path.exists(constraint_map_json_path):
        return jsonify({'error': 'File not found'}), 404

    # Read file and return JSON content
    with open(constraint_map_json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        # print("data: ", data)
        return jsonify(data)

@app.route('/api/get_finalValidation', methods=['GET'])
def api_get_finalValidation(): 
    # Check file exists
    if not os.path.exists(new_json_file_path):
        return jsonify({'error': 'File not found'}), 404

    # Read file and return JSON content
    with open(new_json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        # print("data: ", data)
        return jsonify(data)

@app.route('/api/get_new_finalValidation', methods=['GET'])
def api_get_new_finalValidation(): 
    # Check file exists
    if not os.path.exists(new_json_file_path):
        return jsonify({'error': 'File not found'}), 404

    # Read file and return JSON content
    with open(new_json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        # print("data: ", data)
        return jsonify(data)

@app.route('/api/download_validation_rules', methods=['GET'])
def api_download_validation_rules():
    try:
        if not new_json_file_path or not os.path.exists(new_json_file_path):
            return jsonify({'error': 'File not found'}), 404

        filename = os.path.basename(new_json_file_path)
        response = send_file(
            new_json_file_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        # Allow frontend to read Content-Disposition to get filename
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_detect_functions', methods=['GET'])
def api_download_detect_functions():
    try:
        dataset_label = current_dataset
        if not dataset_label and csv_file_path:
            dataset_label = os.path.basename(os.path.dirname(csv_file_path))
        dataset_label = dataset_label or 'dataset'

        debug_info = {
            'dataset_label': dataset_label,
            'current_dataset': current_dataset,
            'csv_file_path': csv_file_path,
            'csv_exists': bool(csv_file_path and os.path.exists(csv_file_path)),
            'rule_file_path': new_json_file_path,
            'rule_exists': bool(new_json_file_path and os.path.exists(new_json_file_path)),
            'table_info_path': table_json_path,
            'table_info_exists': bool(table_json_path and os.path.exists(table_json_path)),
        }
        print(f"[download_detect_functions] start with {json.dumps(debug_info, ensure_ascii=False)}")

        script_content, filename = build_detection_script(
            csv_path=csv_file_path,
            rule_path=new_json_file_path,
            table_info_path=table_json_path,
            dataset_name=dataset_label,
        )

        response = make_response(script_content)
        response.headers['Content-Type'] = 'text/x-python'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response
    except ValueError as exc:
        print(f"[download_detect_functions] value error: {exc}")
        return jsonify({'error': str(exc), 'debug': debug_info}), 400
    except Exception as exc:
        print(f"[download_detect_functions] unexpected error: {exc}")
        return jsonify({'error': str(exc), 'debug': debug_info}), 500
    
@app.route('/api/get_sort_conditions', methods=['POST'])
def api_get_sort_conditions():
    data = request.get_json()
    column_name = data.get('column_name')
    sort_conditions = load_sort_conditions(new_json_file_path, column_name)
    sort_number = len(sort_conditions) // 2
    # Prepare sort conditions for frontend
    processed_sort_conditions = []
    name_list = ['first', 'second', 'third']
    # Iterate over possible sort fields
    for i in range(1, sort_number + 1):
        column_key = f"{name_list[i-1]}OrderColumn"
        type_key = f"{name_list[i-1]}OrderType"
        
        # Only process when both column and order keys exist
        if column_key in sort_conditions and type_key in sort_conditions:
            # Format matching values for the frontend
            processed_sort_conditions.append({
                'columnName': sort_conditions[column_key],  # Column name
                'order': sort_conditions[type_key].lower()  # Order type normalized to lowercase (Asc/Desc)
            })

    return jsonify({'sort_conditions': processed_sort_conditions})

@app.route('/api/get_multi_difference_sort_conditions', methods=['POST'])
def api_get_multi_difference_sort_conditions():
    try:
        data = request.get_json()
        column_names = data.get('columnNames', [])
        
        # Load sort conditions
        sort_conditions = load_multi_difference_order_condition_json(new_json_file_path, column_names)
        
        # Format sort conditions for the frontend
        processed_sort_conditions = []
        name_list = ['first', 'second', 'third']
        
        # Count available sort conditions
        sort_number = 0
        for name in name_list:
            if f"{name}OrderColumn" in sort_conditions and f"{name}OrderType" in sort_conditions:
                sort_number += 1
        
        # Iterate through possible sort fields
        for i in range(1, sort_number + 1):  # Range is 1 to sort_number
            column_key = f"{name_list[i-1]}OrderColumn"  # Build column key for this index
            type_key = f"{name_list[i-1]}OrderType"  # Build order type key for this index
            
            # Only process when both column and order keys exist
            if column_key in sort_conditions and type_key in sort_conditions:
                # Format matching values for the frontend
                processed_sort_conditions.append({
                    'columnName': sort_conditions[column_key],  # Column name
                    'order': sort_conditions[type_key].lower()  # Order type normalized to lowercase
                })

        return jsonify({'sort_conditions': processed_sort_conditions})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/invalid_pairs_to_indices', methods=['POST'])
def api_invalid_pairs_to_indices():
    data = request.get_json()
    invalid_pairs = data.get('invalid_pairs')
    invalid_indices = invalid_pairs_to_indices(invalid_pairs)
    return jsonify({'invalid_indices': invalid_indices})

@app.route('/api/invalid_pairs_to_sorted_indices', methods=['POST'])
def api_invalid_pairs_to_sorted_indices():
    data = request.get_json()
    invalid_pairs = data.get('invalid_pairs')
    sorted_indices = invalid_pairs_to_sorted_indices(invalid_pairs)
    return jsonify({'sorted_indices': sorted_indices})

@app.route('/api/detect_conflict_flag', methods=['POST'])
def api_detect_conflict_flag():
    try:
        # Parse JSON request body
        data = request.get_json()
        invalid_indices = data.get('invalid_indices', [])
        
        # Run conflict flag detection
        conflict_flag = detect_conflict_flag(invalid_indices, csv_file_path)
        
        # Return response
        return jsonify({'conflict_flag': conflict_flag}), 200
    except Exception as e:
        # Handle errors
        return jsonify({'error': str(e)}), 400

@app.route('/api/refine_validation_rules', methods=['POST'])
def api_refine_validation_rules():
    try:
        # Read request payload
        data = request.get_json()
        
        # Extract required params
        valid_flag = data.get('validFlag', False)
        select_info = data.get('selectInfo', {})
        # Read validation dictionary from file
        validation_dict_path = new_json_file_path
        data_path = csv_file_path
            
        # Run rule refinement
        result = refine_validation_rules(
            validation_dict_path,
            valid_flag,
            data_path,
            select_info,
            model=get_model_from_workflow()
        )
        def replace_non_serializable(data):
            if isinstance(data, dict):
                return {key: replace_non_serializable(value) for key, value in data.items()}
            elif isinstance(data, list):
                return [replace_non_serializable(item) for item in data]
            elif isinstance(data, float) and math.isnan(data):
                return None  # Replace NaN with None
            elif hasattr(data, 'dtype') and np.issubdtype(data.dtype, np.integer):
                return int(data)  # Cast numpy integer to Python int
            elif hasattr(data, 'dtype') and np.issubdtype(data.dtype, np.floating):
                return float(data)  # Cast numpy float to Python float
            elif hasattr(data, 'item'):
                return data.item()  # Handle other numpy scalar types
            return data
        result = replace_non_serializable(result)
        example_result = generate_example(result)
        # Ensure we return JSON instead of a raw string
        response = jsonify(example_result)
        return response
        
    except Exception as e:
        return jsonify({
            'refineStatus': False,
            'refineDict': {
                'addRules': [],
                'deleteRules': [],
                'updateRules': []
            },
            'error': str(e)
        }), 500

@app.route('/api/get_refine_rules', methods=['POST'])
def api_get_refine_rules():
    try:
        # Read request payload
        data = request.get_json()

        df = pd.read_csv(csv_file_path)
        
        # Persist changes to finalValidation.json
        update_validation_rules(new_json_file_path, data, df)
        regenerate_constraint_map()
        
        # Return success response
        return jsonify({"message": "Rules received and updated successfully"}), 200
    except Exception as e:
        # Handle errors
        return jsonify({'error': str(e)}), 400

@app.route('/api/submit-text', methods=['POST'])
def api_submit_text():
    try:
        # Read request payload
        data = request.get_json()
        input_text = data.get('text', "")
        column_names = data.get('columnNames', [])
        rule_type = data.get('ruleType', "")
        rule_value = data.get('ruleValue', "")
        original_rule = generate_original_rule(new_json_file_path, column_names, rule_type, rule_value)
        result = refine_NL(original_rule, input_text, get_model_from_workflow())
        
        # Normalize column field format in refine result
        if result.get('refineDict') and 'updateRules' in result['refineDict']:
            for rule in result['refineDict']['updateRules']:
                if isinstance(rule.get('column'), list) and len(rule['column']) == 1:
                    rule['column'] = rule['column'][0]
                    
        result_example = generate_example(result)
        csv_data = pd.read_csv(csv_file_path)
        update_validation_rules(new_json_file_path, result_example['refineDict'], csv_data)
        regenerate_constraint_map()
        # Return success response

        return jsonify({"result": {"addRules": [], "deleteRules": [], "updateRules": result_example['refineDict']["updateRules"]}}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/detect_multiple_duplicate', methods=['POST'])
def api_detect_multiple_duplicate():
    data = request.get_json()
    column_names = data.get('columnNames', [])
    df = pd.read_csv(csv_file_path)
    df.replace([None, ''], np.nan, inplace=True)
    column_series = [df[col_name] for col_name in column_names]

    invalid_indices = detect_multi_duplicate(column_series)
    return jsonify({'invalid_indices': invalid_indices})

@app.route('/api/generate_card_example', methods=['POST'])
def api_generate_card_example():
    data = request.get_json()
    column_name = data.get('columnName', [])
    rule_type = data.get('ruleType', "")
    example = generate_card_example(new_json_file_path, csv_file_path, column_name, rule_type)
    return jsonify({'example': example})

@app.route('/api/get_current_csv_content', methods=['GET'])
def api_get_current_csv_content():
    try:
        # Read the current dataset CSV content
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_content = file.read()
        
        return jsonify({'csvContent': csv_content}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect_multiple_logic_condition', methods=['POST'])
def api_detect_multiple_logic_condition():
    try:
        # Read request payload
        data = request.get_json()
        selected_columns = data.get('selectedColumns', [])
        
        # Validate input parameters
        if not selected_columns or len(selected_columns) < 3:
            return jsonify({"error": "at least three column names"}), 400
            
        # Read CSV data
        df = pd.read_csv(csv_file_path)
        df.replace([None, ''], np.nan, inplace=True)
        
        # Load multi-column condition logic rules
        multiple_condition_logic = load_multiple_condition_logic(new_json_file_path, selected_columns)
        
        if not multiple_condition_logic:
            return jsonify({"error": "no matching multiple condition logic rule"}), 404
            
        # Detect rows violating logic conditions
        invalid_indices, formatted_rules = detect_multiple_logic_condition(df, multiple_condition_logic)

        return jsonify({'invalid_indices': invalid_indices, 'formatted_rules': formatted_rules}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_rule_creation_info', methods=['GET'])
def api_get_rule_creation_info():
    global new_json_file_path, json_file_path, table_json_path
    
    target_path = new_json_file_path if new_json_file_path and os.path.exists(new_json_file_path) else json_file_path
    
    if not target_path or not os.path.exists(target_path):
        return jsonify({"columns": [], "rules": {}, "columnValues": {}})
        
    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        excluded_keys = [
            "domainDescription", "numericCompareList", "dateCompareList", "conditionLogicColumnList", 
            "multiDifference", "multipleDuplicateColumnsList", 
            "multipleConditionLogicColumnList", "substringList", "lookupList"
        ]
        
        columns = [key for key in data.keys() if key not in excluded_keys]
        
        column_values = {}
        if table_json_path and os.path.exists(table_json_path):
            try:
                with open(table_json_path, 'r', encoding='utf-8') as f:
                    table_info = json.load(f)
                    for col, info in table_info.items():
                        if info.get('type') == 'character':
                            values = [str(item['value']) for item in info.get('valueList', [])]
                            column_values[col] = values
            except Exception as e:
                print(f"Error reading table info: {e}")

        return jsonify({"columns": columns, "rules": data, "columnValues": column_values})
    except Exception as e:
        print(f"Error reading columns: {e}")
        return jsonify({"columns": [], "rules": {}, "columnValues": {}})


@app.route('/api/nlpanel', methods=['POST'])
def api_nlpanel():
    data = request.json or {}
    nl_text = data.get('naturalLanguage', '')
    rule_context = data.get('ruleContext')
    create_rule_payload = data.get('createRule')
    preview_only = bool(data.get('previewOnly'))
    apply_changes = not preview_only

    intent_result = detect_nl_intent(
        nl_text,
        workflow_mode=workflow_mode,
        model=get_model_from_workflow(),
    )

    response_payload = {"intentResult": intent_result, "previewOnly": preview_only}

    if not intent_result.get("status"):
        return jsonify(response_payload), 400

    intent = intent_result.get("intent")

    if rule_context:
        response_payload["ruleContext"] = rule_context

    # Auto-locate rule context when not provided
    if not rule_context and new_json_file_path and os.path.exists(new_json_file_path):
        try:
            with open(new_json_file_path, 'r', encoding='utf-8') as f:
                validation_data = json.load(f)
            available_columns = [k for k in validation_data.keys() if isinstance(validation_data.get(k), dict) and validation_data.get(k).get('type')]
            guess = locate_rule_type_and_columns(
                nl_text,
                available_columns,
                model=get_model_from_workflow(),
                workflow_mode=workflow_mode,
            )
            rule_type = guess.get('ruleType') or guess.get('rule_type')
            columns_list = guess.get('columnsList') or guess.get('columns_list') or []
            validation_rule = None
            if rule_type and columns_list:
                validation_rule = extract_rule_from_validation(rule_type, columns_list, validation_data)
            if rule_type and columns_list and validation_rule is not None:
                rule_context = {
                    "ruleType": rule_type,
                    "columnsList": columns_list,
                    "validationRule": validation_rule,
                }
                response_payload["autoLocated"] = {
                    "ruleType": rule_type,
                    "columnsList": columns_list,
                }
                response_payload["ruleContext"] = rule_context
            else:
                response_payload["autoLocateWarning"] = "Could not infer rule context from NL"
        except Exception as exc:  # noqa: BLE001
            response_payload["autoLocateWarning"] = f"auto locate failed: {exc}"

    if intent == "modify_existing_rule":
        if not rule_context:
            response_payload["error"] = "ruleContext missing for modify_existing_rule"
            return jsonify(response_payload), 400

        try:
            refine_result = refine_NL(
                rule_context,
                nl_text,
                model=get_model_from_workflow(),
            )
            response_payload["refineResult"] = _normalize_refine_result_for_frontend(
                refine_result
            )
            response_payload["applied"] = False

            if refine_result.get("refineStatus"):
                if apply_changes and csv_file_path and new_json_file_path:
                    df = pd.read_csv(csv_file_path)
                    update_validation_rules(
                        new_json_file_path,
                        refine_result.get("refineDict", {}),
                        df,
                    )
                    regenerate_constraint_map()
                    response_payload["updatedValidationPath"] = new_json_file_path
                    response_payload["applied"] = True
        except Exception as exc:  # noqa: BLE001
            response_payload["error"] = str(exc)
            return jsonify(response_payload), 500

    if intent == "create_new_rule" and create_rule_payload:
        try:
            response_payload["applied"] = False
            if apply_changes and csv_file_path and new_json_file_path:
                df = pd.read_csv(csv_file_path)
                update_validation_rules(
                    new_json_file_path,
                    {"addRules": [create_rule_payload]},
                    df,
                )
                regenerate_constraint_map()
                response_payload["createdRule"] = create_rule_payload
                response_payload["updatedValidationPath"] = new_json_file_path
                response_payload["applied"] = True
            else:
                response_payload["createdRule"] = create_rule_payload
        except Exception as exc:  # noqa: BLE001
            response_payload["error"] = str(exc)
            return jsonify(response_payload), 500

    # Preview fallback: if previewOnly and we have a rule_context but no refineResult, still call refine_NL
    if preview_only and rule_context and not response_payload.get("refineResult"):
        try:
            refine_result = refine_NL(
                rule_context,
                nl_text,
                model=get_model_from_workflow(),
            )
            response_payload["refineResult"] = _normalize_refine_result_for_frontend(
                refine_result
            )
        except Exception as exc:  # noqa: BLE001
            response_payload["error"] = f"preview refine failed: {exc}"
            return jsonify(response_payload), 500

    return jsonify(response_payload)


if __name__ == '__main__':
    app.run(port=8081, debug=True)
