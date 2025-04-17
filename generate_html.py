import yaml
import json
import os
import sys
import html
import re
import logging
from collections import defaultdict
import argparse
import hashlib  
import glob

# Setup logging with DEBUG level to capture detailed information during execution
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def load_yaml(yaml_file):
    """
    Loads a YAML file and returns its contents as a Python dictionary.

    Args:
        yaml_file (str): The path to the YAML file.

    Returns:
        dict: The contents of the YAML file as a Python dictionary.
    """
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)

def generate_skeleton_dict(validations,
                           type_keys,
                           encoding_value,
                           validation_yaml,
                           type_values,
                           validations_in_json=None):
    """
    Builds the skeleton dictionary for each gNMI operation type.
    Adds only those validations that appear in the JSON (i.e., in validations_in_json).

    Args:
        validations (str): The current validation key being processed.
        type_keys (list): List of type keys to consider.
        encoding_value (str): Encoding information, if any.
        validation_yaml (str): Path to the YAML validation file.
        type_values (str): Values associated with the types.
        validations_in_json (set, optional): Set of validation keys present in the JSON test results.

    Returns:
        dict: A skeleton dictionary structured for each supported type with relevant validations.
    """
    # Initialize the skeleton dictionary
    skeleton_dict = {}
    # Load validation data from the provided YAML file
    data = load_yaml(validation_yaml)
    
    # Extract relevant sections from the YAML data
    gnmi_operations = data.get('gnmi_operations', {})
    gnmi_operation_validations = data.get('gnmi_operation_validations', {})
    main_validations = data.get('validations', {})
    
    # Get the specific operation data based on the current validation key
    operation_data = gnmi_operations.get(validations, {})
    types = operation_data.get('type', {})
    
    def initialize_type_structure(key):
        """
        Initializes the structure for a given type key.

        Args:
            key (str): The type key to initialize.

        Returns:
            dict: A dictionary with predefined keys and default values.
        """
        return {
            "parent_key": validations,
            "status": "NA",
            "message": [],
            "log": "NA",
            "gnmi_log": "NA",
            "test_log": "NA",
            "Compliance": [],
            "encoding": [],
            "total_validations": "NA",
            "ignored_validations": "NA",
            "failed_validations": "NA",
            "passed_validations": "NA",
            "coverage": "NA"
        }
    
    # Iterate through each type within the current operation
    for key, value in types.items():
        logger.debug(f'Processing main key: {key}, value: {value}')
        # Check if the current type key is in the provided list of type_keys
        if key in type_keys:
            logger.debug(f'Key "{key}" is in type_keys: {type_keys}')
            # Retrieve the current status of the type
            current_status = value.get('current_status', 'not-supported')
            if current_status.lower() != 'supported':
                # Skip unsupported types
                logger.debug(f"Type '{key}' is not supported. Skipping.")
                continue
            
            # Initialize the skeleton structure for the type if not already present
            if key not in skeleton_dict:
                skeleton_dict[key] = initialize_type_structure(key)
                logger.debug(f"Initialized skeleton for type '{key}'.")
            
            # Retrieve the sequence of validations associated with the operation
            operation_validations_sequence = value.get('operation_validations_sequence', [])
            for validation_key in operation_validations_sequence:
                logger.debug(f'Processing validation_key: {validation_key}')
                # Get validation data for the current validation key
                validation_data = gnmi_operation_validations.get(validation_key, {})
                validation_status = validation_data.get('current_status', 'not-supported')
                if validation_status.lower() != 'supported':
                    # Skip unsupported validations
                    logger.debug(f"Validation '{validation_key}' is not supported. Skipping.")
                    continue
                
                # Retrieve the list of validation keys under the current validation
                validation_list = validation_data.get('validations', [])
                for val_key in validation_list:
                    logger.debug(f'Processing val_key: {val_key}')
                    # Get detailed validation data
                    val_data = main_validations.get(val_key, {})
                    val_data_description = val_data.get('description', "")
                    val_current_status = val_data.get('current_status', 'not-supported')
                    if val_current_status.lower() != 'supported':
                        # Skip validations that are not supported
                        logger.debug(f"Validation '{val_key}' is not supported. Skipping.")
                        continue
                    # Skip validations not present in the JSON test results
                    if validations_in_json and val_key not in validations_in_json:
                        logger.debug(f"Validation '{val_key}' not found in JSON data. Skipping.")
                        continue
                    
                    # Add the validation to the Compliance list in the skeleton dictionary
                    skeleton_dict[key]["Compliance"].append({
                        val_key: {},  # Initialize without 'message' and 'status'
                        'description': val_data_description,
                        'key': type_values
                    })
                    logger.debug(f"Added compliance for validation '{val_key}' to type '{key}'.")
            # Add encoding information if provided
            if encoding_value:
                skeleton_dict[key]["encoding"].append({"value": encoding_value})
                logger.debug(f"Added encoding '{encoding_value}' to type '{key}'.")
        else:
            # Handle types not present in type_keys
            current_status = value.get('current_status', 'not-supported')
            if current_status == 'not-supported':
                # Skip unsupported types
                logger.debug(f"Type '{key}' is not supported. Skipping.")
                continue
            # Initialize the skeleton structure for unsupported types
            skeleton_dict[key] = initialize_type_structure(key)
            logger.debug(f"Initialized skeleton for unsupported type '{key}'.")
    
    return skeleton_dict


def process_directory(yaml_file, directory, output_folder="logs"):
    directory = os.path.abspath(directory)
    
    # Use glob to list files that match the expected patterns.
    json_pattern = os.path.join(directory, "*-tc_result.json")
    log_pattern = os.path.join(directory, "*-tc_result.log")
    
    json_files = {}
    for filepath in glob.glob(json_pattern):
        base = os.path.basename(filepath)
        suffix = "-tc_result.json"
        if base.endswith(suffix):
            prefix = base[:-len(suffix)]
            json_files[prefix] = base

    log_files = {}
    for filepath in glob.glob(log_pattern):
        base = os.path.basename(filepath)
        suffix = "-tc_result.log"
        if base.endswith(suffix):
            prefix = base[:-len(suffix)]
            log_files[prefix] = base

    if not json_files:
        logger.error(f"No valid JSON files found in directory '{directory}'.")
        sys.exit(1)
    

    
    aggregated_report = {}
    yang_model = None  # Will be set from the first file's model

    # Process each JSON file (and its corresponding log file, if available)
    for prefix, json_file in json_files.items():
        json_path = os.path.join(directory, json_file)
        if not os.path.exists(json_path):
            logger.error(f"JSON file '{json_path}' does not exist. Skipping.")
            continue

        log_path = None
        if prefix in log_files:
            candidate = os.path.join(directory, log_files[prefix])
            if os.path.exists(candidate):
                log_path = candidate
        
        logger.info(f"Processing: {json_path}" + (f" with {log_path}" if log_path else " (No Log File)"))
        
        try:
            with open(json_path, "r") as f:
                json_data = json.load(f)
        except Exception as exc:
            logger.error(f"Error reading JSON file '{json_path}': {exc}")
            continue
        
        # Call your function to summarize the test report.
        # It should return a tuple: (report dictionary, yang model name)
        report, model = summarize_test_report(tc_result_filename=json_path, validation_file=yaml_file, log_file=log_path)
        if not yang_model:
            yang_model = model
       
        # Merge the report data into aggregated_report.
        for key, value in report.items():
            if key == 'summary':
                if 'summary' not in aggregated_report:
                    aggregated_report['summary'] = value
                else:
                    for metric, metric_value in value.items():
                        try:
                            aggregated_report['summary'][metric] = int(aggregated_report['summary'][metric]) + int(metric_value)
                        except Exception as e:
                            logger.debug(f"Skipping summary merge for metric '{metric}': {e}")
            else:
                if key not in aggregated_report:
                    aggregated_report[key] = value
                else:
                    i = 1
                    new_key = f"{key}_{i}"
                    while new_key in aggregated_report:
                        i += 1
                        new_key = f"{key}_{i}"
                    aggregated_report[new_key] = value

    # Load the template file. First, try the alternative path then fallback.
    template_file = os.path.join("Report_Generators", "Yang_Tree_HTML", "existing_template.html")
    if not os.path.exists(template_file):
        template_file = os.path.join("existing_template.html")
    if not os.path.exists(template_file):
        logger.error("Template file not found.")
        sys.exit(1)
    
    try:
        with open(template_file, 'r') as file:
            template = file.read()
            logger.debug(f"Loaded HTML template from {template_file}")
    except Exception as e:
        logger.error(f"Error reading template file '{template_file}': {e}")
        sys.exit(1)
    
    # Build hierarchical tree from the aggregated report (using your build_hierarchy function)
    tree = build_hierarchy(aggregated_report)
    
    # Generate the final HTML by replacing the placeholders in the template.
    final_html = template.replace("{{data}}", json.dumps(aggregated_report))
    if yang_model.startswith("Model - "):
        yang_model = yang_model.replace("Model - ", "", 1)

    final_html = final_html.replace("{{heading}}", yang_model if yang_model else "")
    #final_html = final_html.replace("{{heading}}", yang_model if yang_model else "")
  
    final_html = final_html.replace("{{treeData}}", json.dumps(tree))
    
    # Define the output file path
    logs_folder = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(logs_folder, output_folder)
    os.makedirs(logs_dir, exist_ok=True)
    dir_name = os.path.basename(directory)
    output_file = os.path.join(logs_dir, dir_name + "_yang_tree_report.html")
    
    try:
        with open(output_file, "w") as html_file:
            html_file.write(final_html)
        logger.info(f"HTML report generated: {output_file}")
    except Exception as exc:
        logger.error(f"Error writing to output file: {exc}")
        sys.exit(1)


def summarize_test_report(tc_result_filename, path_to_platform_support_dict=None, deviation_list=None, input_yang_model=None, validation_file=None, log_file=None):
    """
    Summarizes the test report by processing the results and extracting 
    relevant information into a dictionary format.

    Args:
        tc_result_filename (str): Path to the JSON test result file.
        path_to_platform_support_dict (dict, optional): Dictionary mapping XPaths to platform support statuses.
        deviation_list (list, optional): List of XPaths that are deviations.
        input_yang_model (str, optional): Name of the input YANG model.
        validation_file (str): Path to the YAML validation file.

    Returns:
        tuple: A tuple containing the summarized report dictionary and the input YANG model name.
    """
    logger.debug(f"Loading test case result file: {tc_result_filename}")
    with open(tc_result_filename, "r") as f:
        data = json.load(f)
    
    xpath_status = {}
    
    # Load YAML validations from the provided validation file
    yaml_data = load_yaml(validation_file)
    main_validations = yaml_data.get("validations", {})
    log_dict={}
    if log_file:
        log_dict = parse_log_file(log_file)
        logger.debug("Parsed log file and obtained log dictionary.")
    # Determine the input YANG model name if not provided
    if not input_yang_model:
        input_yang_model = 'Model - ' + data['labels'][0]
        input_yang_model = input_yang_model.title()
 
    
    # Retrieve platform support information from metadata if not provided
    if not path_to_platform_support_dict:
        if "metadata" in data:
            path_to_platform_support_dict = data["metadata"].get("platform_support", {})
        else:
            path_to_platform_support_dict = {}
    
    # Retrieve deviation list from metadata if not provided
    if not deviation_list:
        if "metadata" in data:
            deviation_list = data["metadata"].get("deviations", [])
        else:
            deviation_list = []
    
    # Dictionary to track the count of each type per XPath to handle duplicates
    path_type_counters = defaultdict(lambda: defaultdict(int))
    
    # Iterate through each test result in the JSON data
    for result in data.get("results", []):
        test_name = result.get("test_name", "")
        logger.debug(f"Processing test name: {test_name}")
        
        # Extract the first part of the test name as the extracted_test_name
        extracted_test_name = test_name.split(' ')[0]
        # Use regex to extract XPath patterns from the test name
        # xpath_matches = re.sub(r'\[.*?\]', '', test_name)
        def xpath_lookup(xpath):
            return re.sub(r'\[.*?\]', '', xpath)
        xpath_matches = re.sub(r'.*<-\s*(.*?)\s*->\s*.*', r'\1', test_name)
        xpath_matches = xpath_lookup(xpath_matches)
        if not xpath_matches:
            # Log an error if the test name does not match the expected pattern
            logger.error(f"Test name does not contain the expected XPath pattern: {test_name}")
            continue

        # Determine the XPath by removing '/dependencies' if present
        xpath = xpath_matches.split('/dependencies')[0] if 'dependencies' in xpath_matches else xpath_matches
        
        # Initialize the xpath_status entry if it's the first occurrence
        if xpath not in xpath_status:
            xpath_status[xpath] = {
                "test_name": extracted_test_name,
                "deviation": {"status": "No", "message": "", "log": ""},
                "platform": {"status": "NN", "message": "", "log": ""},
                "status": {"status": "NA", "message": [], "log": ""},
                "skeleton": True  # Placeholder flag to indicate skeleton structure
            }
            # Initialize the summary section with overall test metrics
            xpath_status['summary'] = {
                "tests_total_validations": data.get('tests_total_validations', 0),
                "tests_passed_validations": data.get('tests_passed_validations', 0),
                "tests_failed_validations": data.get('tests_failed_validations', 0),
                "tests_ignored_validations": data.get('tests_ignored_validations', 0),
                "tests_pass": data.get('tests_pass', 0),
                "tests_total": data.get('tests_total', 0),
                "tests_fail": data.get('tests_fail', 0)
            }
        
        # Extract various log details from the test result
        success = result.get("success", False)
        log_entries = result.get("results", [])
        log_string = log_entries[-1].get("log", "") if log_entries else ""
        gnmi_log = log_entries[-1].get("gnmi_log", "") if log_entries else ""
        test_log = log_entries[-1].get("test_log", "") if log_entries else ""
        total_validations = log_entries[-1].get("total_validations", "") if log_entries else ""
        passed_validations = log_entries[-1].get("passed_validations", "") if log_entries else ""
        failed_validations = log_entries[-1].get("failed_validations", "") if log_entries else ""
        ignored_validations = log_entries[-1].get("ignored_validations", "") if log_entries else ""
        coverage = log_entries[-1].get("coverage", "") if log_entries else ""
        
        # Extract validation operations from the log entries
        operation = log_entries[-1].get("validations", "") if log_entries else ""
        validations = next(iter(operation)) if operation else None
        
        if validations:
            # Retrieve type data and encoding information from the operation
            type_data = operation[validations].get("type", {})
            encoding_value = operation[validations].get("encoding", None)
            # Identify all type keys excluding 'encoding'
            type_keys = [key for key in type_data.keys() if key != "encoding"]
            # Extract type_values for compliance key
            type_values = [value for key, value in type_data.items() if key != "encoding"]
            type_values = next(iter(type_values[0][0].keys())) if type_values else None
            
            # Collect validation keys present in JSON for the current type instance
            current_validation_keys = set()
            for type_key in type_keys:
                type_entries = type_data[type_key]
                for entry in type_entries:
                    for val_key in entry.keys():
                        current_validation_keys.add(val_key)
            
            # Iterate through each type key to handle skeleton and updates
            for type_key in type_keys:
                type_value = type_values  # Assuming type_values is consistent across types
                
                # Increment the counter for this type under the current XPath
                path_type_counters[xpath][type_key] += 1
                type_count = path_type_counters[xpath][type_key]
                
                # Determine a unique type key to handle multiple instances (e.g., ONCE, ONCE_1, etc.)
                if type_count == 1:
                    unique_type_key = type_key
                else:
                    unique_type_key = f"{type_key}_{type_count}"
                
                # Initialize the skeleton for the unique type if it doesn't exist
                if unique_type_key not in xpath_status[xpath]:
                    skeleton_dict = generate_skeleton_dict(
                        validations,
                        [type_key],  # Pass the original type_key to maintain YAML references
                        encoding_value,
                        validation_file,
                        type_values,
                        validations_in_json=current_validation_keys  # Pass per-instance set
                    )
                    # Rename the type key in skeleton_dict to the unique_type_key
                    if type_key in skeleton_dict:
                        skeleton_dict[unique_type_key] = skeleton_dict.pop(type_key)
                    # Update the xpath_status with the new skeleton_dict
                    xpath_status[xpath].update(skeleton_dict)
                else:
                    # If the skeleton already exists, retrieve it
                    skeleton_dict = xpath_status[xpath]
                new_log_data = log_dict.get(test_name, {})  # or .get(test_name, "NA")
                inner_result = log_entries[-1].get("result", None)
                # Update the skeleton_dict with actual test details
                update_skeleton_dict(
                    operations=operation,
                    skeleton_dict=skeleton_dict,
                    log_string=log_string,
                    gnmi_log=gnmi_log,
                    test_log=test_log,
                    status="PASS" if success else "FAIL",
                    validations=validations,
                    total_validations=total_validations,
                    ignored_validations=ignored_validations,
                    failed_validations=failed_validations,
                    passed_validations=passed_validations,
                    coverage=coverage,
                    type_key=unique_type_key,  # Use the unique_type_key here
                    main_validations=main_validations,  # Pass main_validations
                    test_name = test_name,
                    new_log=new_log_data,
                    json_result=inner_result 
                )
                # Update the xpath_status with the modified skeleton_dict
                xpath_status[xpath].update(skeleton_dict)
                # Remove the 'skeleton' placeholder flag as it's no longer needed
                xpath_status[xpath].pop("skeleton", None)
        
        # Update the overall status and handle deviations and platform support
        status = "PASS" if success else "FAIL"
        
        # Check if the current XPath is marked as a deviation
        if xpath in deviation_list:
            xpath_status[xpath]["deviation"]["status"] = "Yes"
            xpath_status[xpath]["deviation"]["message"] = "Deviation Path"
            status += "(D)"  # Append deviation indicator to status
        
        # Retrieve platform support status for the current XPath
        platform = path_to_platform_support_dict.get(xpath, "NN")  # Default to "NN" if not found
        if platform in ["NS", "NA"]:
            # Append platform support status to overall status
            status += f"(P-{platform})"
        # Update platform support status in the summary
        xpath_status[xpath]["platform"]["status"] = platform
        
        # Update the overall status if it hasn't been marked as "FAIL"
        if xpath_status[xpath]["status"]["status"] != "FAIL":
            xpath_status[xpath]["status"]["status"] = status
    
    # After processing all test results, handle the grouping of multiple types
    for xpath, details in xpath_status.items():
        if xpath == 'summary':
            continue  # Skip the summary section
        
        # Identify type keys that are not part of metadata sections
        type_keys = [key for key in details.keys() if key not in ["test_name", "deviation", "platform", "status", "skeleton"]]
        duplicate_types = defaultdict(list)
        
        # Group type keys by their base type to identify duplicates
        for type_key in type_keys:
            base_type = re.sub(r'_\d+$', '', type_key)  # Remove numeric suffixes
            duplicate_types[base_type].append(type_key)
        
        multiple_data = {}
        types_to_remove = []
        
        # Iterate through each base type and its instances
        for base_type, instances in duplicate_types.items():
            if len(instances) > 1:
                # If multiple instances exist, add them to multiple_data
                for instance in instances:
                    multiple_data[instance] = details.pop(instance)
                # Rename the first instance to the base_type
                if instances:
                    multiple_data[base_type] = multiple_data.pop(instances[0])
                types_to_remove.extend(instances)
        
        if multiple_data:
            # Add the grouped multiple_data to the details
            details["multiple_data"] = multiple_data
    
    # Return the summarized report and the input YANG model name
    return xpath_status, input_yang_model

def update_skeleton_dict(operations, skeleton_dict, log_string, gnmi_log, test_log, status, validations, total_validations, ignored_validations, failed_validations, passed_validations, coverage, type_key, main_validations, test_name, new_log,  json_result=None):
    """
    Updates the skeleton_dict with the actual test details for a specific type.

    Args:
        operations (dict): The operations dictionary from the JSON.
        skeleton_dict (dict): The skeleton dictionary to update.
        log_string (str): The log string from the test result.
        gnmi_log (str): The GNMI log from the test result.
        test_log (str): The test log from the test result.
        status (str): The overall status ("PASS" or "FAIL").
        validations (str): The validation key.
        total_validations (int): Total number of validations.
        ignored_validations (int): Number of ignored validations.
        failed_validations (int): Number of failed validations.
        passed_validations (int): Number of passed validations.
        coverage (float): Coverage percentage.
        type_key (str): The current type key (e.g., "ONCE", "STREAM-SAMPLE", "ONCE_1", "ONCE_2").
        main_validations (dict): The main validations dictionary from YAML.

    Returns:
        dict: The updated skeleton dictionary.
    """
    skeleton_dict[type_key]["full_path"] = test_name
    skeleton_dict[type_key]["new_log"] = new_log
    skeleton_dict[type_key]["status"] = json_result if json_result is not None else status
    # Extract the original type name by removing the numeric suffix if present
    original_type_key = re.sub(r'_\d+$', '', type_key)
    # Retrieve the types dictionary from the operations
    types_dict = operations.get(validations, {}).get('type', {})
    # Retrieve encoding information if available
    encoding_value = operations.get(validations, {}).get('encoding', None)
    
    # Check if the original type_key exists in types_dict
    if original_type_key not in types_dict:
        logger.warning(f"Type '{original_type_key}' not found in operations for validations '{validations}'. Skipping update.")
        return skeleton_dict
    
    # Get the list of validations for the original type_key
    validation_list = types_dict[original_type_key]
    # Add encoding information to the skeleton_dict if not already present
    if encoding_value and {"value": encoding_value} not in skeleton_dict[type_key]["encoding"]:
        skeleton_dict[type_key]["encoding"].append({"value": encoding_value})
        logger.debug(f"Added encoding '{encoding_value}' to type '{type_key}'.")
    
    # Iterate through each validation entry in the validation list
    for validation in validation_list:
        for validation_name, validation_results in validation.items():

            if validation_results:
                # Update metadata fields in the skeleton_dict
                # skeleton_dict[type_key]['status'] = status if status else "NA"
                skeleton_dict[type_key]['message'] = []  # Assuming message handling is required
                skeleton_dict[type_key]['log'] = log_string if log_string else "NA"
                skeleton_dict[type_key]['gnmi_log'] = gnmi_log if gnmi_log else "NA"
                skeleton_dict[type_key]['test_log'] = test_log if test_log else "NA"
                skeleton_dict[type_key]['total_validations'] = total_validations if total_validations else "NA"
                skeleton_dict[type_key]['ignored_validations'] = ignored_validations if ignored_validations else "NA"
                skeleton_dict[type_key]['failed_validations'] = failed_validations if failed_validations else "NA"
                skeleton_dict[type_key]['passed_validations'] = passed_validations if passed_validations else "NA"
                skeleton_dict[type_key]['coverage'] = coverage if coverage else "NA"
                logger.debug(f"Updated metadata for type '{type_key}' with status '{status}'.")

            # validation_results is a dict like {'Status_Code': 'PASS', ...}
            for comp_key, comp_value in validation_results.items():
                # Access the Compliance list from the skeleton_dict for the current type_key
                compliance_list = skeleton_dict[type_key].get('Compliance', [])
                for compliance_dict in compliance_list:
                    if comp_key in compliance_dict:
                        # Update the compliance status if the key exists
                        compliance_dict[comp_key] = comp_value
                        logger.debug(f"Updated compliance '{comp_key}' to '{comp_value}' for type '{type_key}'.")
                        break
                else:
                    # If the compliance key doesn't exist, add it with description and key
                    validation_info = main_validations.get(comp_key, {})
                    description = validation_info.get('description', "")
                    key_name = validation_info.get('name', "")
                    skeleton_dict[type_key]['Compliance'].append({
                        comp_key: comp_value,
                        'description': description,
                        'key': key_name
                    })
                    logger.debug(f"Added new compliance '{comp_key}' with status '{comp_value}' to type '{type_key}'.")

    return skeleton_dict

def parse_log_file(log_file):
    """
    Parses the provided log file to extract test case logs.
    For each test case block starting with [TESTCASE-BEGIN], it extracts the header and log content.
    The extracted test case name (the text immediately following the test case number) is stored as a dictionary entry,
    with a sub-dictionary that has two keys:
      - "path": containing the extracted test case name
      - "data": containing the full log content (including the header)
      
    Args:
        log_file (str): Path to the log file.
    
    Returns:
        dict: A dictionary mapping the extracted test case name to a dictionary with keys "path" and "data".
    """
    new_logs = {}
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as lf:
            content = lf.read()
    except Exception as e:
        logger.error(f"Error reading log file {log_file}: {e}")
        return new_logs

    # Split the log content by the marker "[TESTCASE-BEGIN]"
    blocks = content.split("[TESTCASE-BEGIN]")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if len(lines) >= 3 and lines[0].startswith('+') and lines[1].startswith('|') and lines[2].startswith('+'):
            # Extract the header line from the block and clean it
            header_line = lines[1].strip('|').strip()
            # Split the header line on "->"
            parts = header_line.split("->", 1)
            if len(parts) >= 2:
                # The test case name is assumed to be the text right after the test case number.
                key_name = parts[1].strip()
            else:
                key_name = header_line
            # Instead of removing the header, include all lines as the log content.
            log_content = "\n".join(lines).strip()
            new_logs[key_name] = {"path": key_name, "data": log_content}
        else:
            # Fallback: attempt to find a header line enclosed in '|'
            for idx, line in enumerate(lines):
                if line.startswith('|') and line.endswith('|'):
                    header_line = line.strip('|').strip()
                    parts = header_line.split("->")
                    if len(parts) >= 2:
                        key_name = parts[1].strip()
                    else:
                        key_name = header_line
                    # Keep the entire block intact
                    log_content = "\n".join(lines).strip()
                    new_logs[key_name] = {"path": key_name, "data": log_content}
                    break
    return new_logs


def generate_html_from_yaml(yaml_file, json_file, template_file, output_file, log_file=None):
    """
    Generates the final HTML by processing YAML, JSON, template, and optionally a log file.

    Parameters:
        yaml_file (str): Path to the YAML file.
        json_file (str): Path to the JSON result file.
        template_file (str): Path to the HTML template file.
        output_file (str): Path to the output HTML file.
        log_file (str, optional): Path to the log file.

    Returns:
        None
    """
    # Summarize the test report by processing the JSON and YAML files
    summarized_report, input_yang_model = summarize_test_report(tc_result_filename=json_file, validation_file=yaml_file, log_file=log_file)
    logger.debug("Summarized test report.")
   

    try:
        # Load the HTML template file
        with open(template_file, 'r') as file:
            template = file.read()
            logger.debug(f"Loaded HTML template from {template_file}")
    except FileNotFoundError:
        # Log an error and exit if the template file is not found
        logger.error(f"Template file '{template_file}' not found.")
        sys.exit(1)

    # Build a hierarchical tree structure from the summarized report
    tree = build_hierarchy(summarized_report)
    
    # Replace placeholders in the template with actual data
    final_html = template.replace("{{data}}", json.dumps(summarized_report))
    final_html = final_html.replace("{{heading}}", json.dumps(input_yang_model))
    final_html = final_html.replace("{{treeData}}", json.dumps(tree))
    
    # Write the populated HTML content to the output file
    try:
        with open(output_file, "w") as html_file:
            html_file.write(final_html)
        logger.info(f"HTML report generated: {output_file}")
    except Exception as exc:
        # Log any errors encountered during file writing and exit
        logger.error(f"Error writing to output file: {exc}")
        sys.exit(1)

def build_hierarchy(data_obj):
    """
    Constructs a hierarchical tree structure from the summarized data.
    
    For each full path in data_obj, the hierarchy is built by splitting on "/". 
    For intermediate nodes (i.e. not the final component) the _data is set to "NA".
    Only the final node receives the actual value from data_obj.
    
    Args:
        data_obj (dict): The summarized test report dictionary.
    
    Returns:
        dict: A nested dictionary representing the hierarchical structure.
    """
    tree = {}

    def get_node(current_tree, path):
        """
        Retrieves the node corresponding to the given path.
        Returns None if the node doesn't exist.
        """
        components = [comp for comp in path.split("/") if comp]
        current = current_tree
        accumulated_path = ""
        for comp in components:
            accumulated_path = f"{accumulated_path}/{comp}" if accumulated_path else comp
            if accumulated_path not in current:
                return None
            current = current[accumulated_path]
        return current

    # Process each full_path in the data object
    for full_path, value in data_obj.items():
        # Handle keys that include "->" by updating an existing node if found.
        if "->" in full_path:
            base = full_path.split("->")[0].strip()
            node = get_node(tree, base)
            if node is not None:
                node["_data"] = value
                continue

        # Split the full path into its components.
        components = [comp for comp in full_path.strip().split("/") if comp]
        current = tree
        accumulated_path = ""
        for idx, component in enumerate(components):
            # Build the accumulated path (which is used as the key)
            accumulated_path = f"{accumulated_path}/{component}" if accumulated_path else component
            # If node does not exist, create it.
            if accumulated_path not in current:
                if idx == len(components) - 1:
                    # For the final (leaf) node, store the actual value.
                    current[accumulated_path] = {"_data": value}
                else:
                    # For intermediate nodes, always store "NA"
                    current[accumulated_path] = {"_data": "NA"}
            else:
                # If the node exists and it's an intermediate node, force _data to "NA".
                if idx != len(components) - 1:
                    current[accumulated_path]["_data"] = "NA"
            current = current[accumulated_path]

    return tree

def main(yaml_file, json_file, log_file=None, output_folder="logs"):
    """
    Main function to handle command-line arguments and trigger the HTML generation process.

    Supports:
    1. Running with a single JSON file (with or without a log file).
    2. Running with a directory containing multiple JSON and log files.

    Ensures the correct file format:
    - JSON file must end with "_result.json"
    - Log file (if provided) must end with "_tc_result.log"
    """

    if os.path.isdir(json_file):
        # If a directory is provided, process all valid JSON and LOG file pairs and generate one consolidated HTML report
        process_directory(yaml_file, json_file)
        return  # Exit after processing the directory

    # Existing validation logic (unchanged)
    
    if not json_file.endswith("_result.json"):
        logger.error(f"Invalid JSON file format: '{json_file}'. It must end with '_result.json'.")
        sys.exit(1)

    if log_file and not log_file.endswith("-tc_result.log"):
        logger.error(f"Invalid Log file format: '{log_file}'. It must end with '-tc_result.log'.")
        sys.exit(1)


    # Determine the base directory of the script (2 levels up if inside Report_Generators)
    # logs_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    logs_folder = os.path.dirname(os.path.abspath(__file__))


    # Define the logs folder at the correct level
    logs_dir = os.path.join(logs_folder, output_folder)
    os.makedirs(logs_dir, exist_ok=True)

    # Set the template path dynamically
    alternative_template_path = os.path.join("Report_Generators/Yang_Tree_HTML/existing_template.html")
     # OR if the file is in the current directory
    main_template_path = os.path.join("existing_template.html")
    

    if os.path.exists(alternative_template_path):
        template_file = alternative_template_path
    else:
        template_file = main_template_path

    output_file = os.path.join(logs_dir, os.path.splitext(os.path.basename(json_file))[0] + "_yang_tree_report.html")
  


    for file_path, desc in [(yaml_file, "YAML file"), (json_file, "JSON file"), (template_file, "Template file")]:
        if not os.path.isfile(file_path):
            logger.error(f"{desc} '{file_path}' does not exist.")
            sys.exit(1)

    if log_file and not os.path.isfile(log_file):
        logger.error(f"Log file '{log_file}' does not exist.")
        sys.exit(1)

    # Generate the HTML report for a single file (existing logic)
    generate_html_from_yaml(yaml_file, json_file, template_file, output_file, log_file)


if __name__ == "__main__":
    # Argument parsing to support both cases (with or without log file)
    parser = argparse.ArgumentParser(description="Generate HTML report from YAML and JSON files.")
    parser.add_argument("yaml_file", help="Path to the validation.yaml file")
    parser.add_argument("json_file", help="Path to the <idp>.json result file or directory")
    parser.add_argument("log_file", nargs="?", default=None, help="Optional log file")

    args = parser.parse_args()

    # Run the main function with the provided arguments
    main(args.yaml_file, args.json_file, args.log_file)
