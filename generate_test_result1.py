import os
import sys
import json
import re

def extract_xpath(test_name):
    """
    Extracts the xpath portion from a test name string.
    For example, if test_name is:
      "Sets and Get <- /system/aaa/accounting/events/event[event-type=AAA_ACCOUNTING_EVENT_COMMAND]/config/event-type -> AAA_AUTHORIZATION_EVENT_COMMAND"
    This function returns:
      "/system/aaa/accounting/events/event[event-type=AAA_ACCOUNTING_EVENT_COMMAND]/config/event-type"
    If the pattern is not found, returns the full test_name.
    """
    return re.sub(r'\[.*?\]', '', test_name.split("<-")[1].split("->")[0].strip()) if "<-" in test_name and "->" in test_name else test_name

def parse_log_files_from_directory(directory):
    """
    Parse all JSON files in the specified directory and combine the results into a single JSON object.
    """
    combined_data = []  # Initialize as an empty list to hold all the JSON data
    
    for filename in os.listdir(directory):
        if filename.endswith("_result.json"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)  # Load the JSON data from the file
                    if isinstance(data, list):
                        combined_data.extend(data)
                    elif isinstance(data, dict):
                        combined_data.append(data)
                    else:
                        print(f"Unexpected data format in {filename}")
                        continue
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                continue
    
    with open('combined_data.json', 'w', encoding='utf-8') as txt_file:
        json.dump(combined_data, txt_file, indent=4)
    
    return combined_data

def dict_data_handling(files, filename_result):
    # Initialize counters and other variables for summing purposes
    tests_total_validations = 0 
    tests_passed_validations = 0
    tests_failed_validations = 0
    tests_ignored_validations = 0
    tests_pass = 0
    tests_total = 0
    tests_fail = 0
    model_info = "N/A"
    model_info_str = set()
    actual_test_release = ""
    test_release = ""
    actual_test_platform = ""
    test_platform = ""
    overall_result = "FAIL"
    total_deviations = 0
    total_paths = 0
    set_xpaths = 0
    state_only = 0
    set_get_sub = 0
    deviations_count = 0
    input_xpaths = 0
    input_state_xpaths = 0
    test_set_get_sub = 0
    test_state = 0
    test_xpaths = 0
    test_coverage = 0
    test_coverage_str = "0.00% [0/0]"
    pure_failures = 0
    deviation_failures = 0
    detail_rows = ""
    platform_support_summary = ""
    
    if isinstance(files, list):
        # First pass: Sum the numeric fields from each file
        for data in files:
            tests_total_validations += data.get("tests_total_validations", 0)
            tests_passed_validations += data.get("tests_passed_validations", 0)
            tests_failed_validations += data.get("tests_failed_validations", 0)
            tests_ignored_validations += data.get("tests_ignored_validations", 0)
            tests_pass += data.get("tests_pass", 0)
            tests_total += data.get("tests_total", 0)
            tests_fail += data.get("tests_fail", 0)
            
            metadata = data.get("metadata", {})
            summary = metadata.get("summary_dict", {})
            total_deviations += metadata.get("total_deviations", 0)
            total_paths += summary.get("total_xpaths", 0)
            set_xpaths += summary.get("set_xpaths", 0)
            state_only += summary.get("state_only", 0)
            set_get_sub += summary.get("set_get_sub", 0)
            deviations_count += summary.get("deviations", 0)
            input_xpaths += summary.get("input_xpaths", 0)
            input_state_xpaths += summary.get("input_state_xpaths", 0)
            test_set_get_sub += summary.get("test_set_get_sub", 0)
            test_state += summary.get("test_state", 0)
            test_xpaths += summary.get("test_xpaths", 0)
            test_coverage += summary.get("test_coverage", 0)

            # Collate release and platform info as before
            actual_test_release_str = summary.get("actual_test_release", [])
            existing_releases = set(actual_test_release.split(", ")) if actual_test_release else set()
            if isinstance(actual_test_release_str, list):
                for release in actual_test_release_str:
                    if str(release) not in existing_releases:
                        if actual_test_release:
                            actual_test_release += ", "
                        actual_test_release += str(release)
                        existing_releases.add(str(release))
            else:
                if str(actual_test_release_str) not in existing_releases:
                    if actual_test_release:
                        actual_test_release += ", "
                    actual_test_release += str(actual_test_release_str)

            test_release_str = summary.get("test_release", [])
            existing_releases = set(test_release.split(", ")) if test_release else set()
            if isinstance(test_release_str, list):
                for release in test_release_str:
                    if str(release) not in existing_releases:
                        if test_release:
                            test_release += ", "
                        test_release += str(release)
                        existing_releases.add(str(release))
            else:
                if str(test_release_str) not in existing_releases:
                    if test_release:
                        test_release += ", "
                    test_release += str(test_release_str)
            
            test_platform_str = summary.get("test_platform", [])
            existing_platforms = set(test_platform.split(", ")) if test_platform else set()
            if isinstance(test_platform_str, list):
                for platform in test_platform_str:
                    if str(platform) not in existing_platforms:
                        if test_platform:
                            test_platform += ", "
                        test_platform += str(platform)
                        existing_platforms.add(str(platform))
            else:
                if str(test_platform_str) not in existing_platforms:
                    if test_platform:
                        test_platform += ", "
                    test_platform += str(test_platform_str)
            
            platform_support_summary_str = summary.get("platform_support", [])
            existing_platform_supports = set(platform_support_summary.split(", ")) if platform_support_summary else set()
            if isinstance(platform_support_summary_str, list):
                for platform in platform_support_summary_str:
                    if str(platform) not in existing_platform_supports:
                        if platform_support_summary:
                            platform_support_summary += ", "
                        platform_support_summary += str(platform)
                        existing_platform_supports.add(str(platform))
            else:
                if str(platform_support_summary_str) not in existing_platform_supports:
                    if platform_support_summary:
                        platform_support_summary += ", "
                    platform_support_summary += str(platform_support_summary_str)

        if total_paths > 0:
            test_coverage = (test_xpaths / total_paths) * 100
            test_coverage_str = f"{test_coverage:.2f}% [{test_xpaths}/{total_paths}]"
    
        detail_rows = ""
        s_no = 1
        file_list = files if isinstance(files, list) else [files]

        # Second pass: Build detail rows for each file
        test_id_counter = {}
        for data in file_list:
            deviation_platform_count = 0
            results = data.get("results", [])
            # FIX: Define deviations and platform_support for this file from its metadata
            deviations = data.get("metadata", {}).get("deviations", {})
            platform_support = data.get("metadata", {}).get("platform_support", {})

            for result in sorted(results, key=lambda r: int(re.findall(r'\d+', r.get("test_id", "0"))[0])):
                test_id = result.get("test_id", "")
                # New unique key generation using a counter
                current_count = test_id_counter.get(test_id, 0) + 1
                test_id_counter[test_id] = current_count
                unique_test_id = test_id if current_count == 1 else f"{test_id}_{current_count}"
               
                testcase = result.get("test_name", "")
                if "<-" in testcase and "->" in testcase:
                    before = testcase.split("<-")[0].strip()
                    bold_part = testcase.split("<-")[1].split("->")[0].strip()
                    after = testcase.split("->")[1].strip()
                    testcase = f'{before} <- <b>{bold_part}</b> -> {after}'

                inner_results = result.get("results", [])
                if inner_results:
                    validations = inner_results[0].get("validations", {})
                    section_name = next(iter(validations), None)
                    op_dict = validations.get(section_name, {}).get("type", {})
                    if op_dict:
                        op_type = list(op_dict.keys())[0]
                        if op_type == "UPDATE":
                            testcase_operation = "SET - " + op_type + " & GET" 
                        elif op_type in ["DELETE", "REPLACE"]:
                            testcase_operation = "SET - " + op_type
                        else:
                            if "SUBSCRIBE" in section_name.upper():
                                testcase_operation = "SUBSCRIBE - " + op_type
                            else:
                                testcase_operation = section_name.upper()
                    else:
                        testcase_operation = testcase.split("<-")[0].strip() if "<-" in testcase else testcase
                else:
                    testcase_operation = testcase.split("<-")[0].strip() if "<-" in testcase else testcase
                
                test_id = result.get("test_id", "")
                xpath = extract_xpath(testcase)
                success = "PASS" if result.get("success", False) else "FAIL"
                testcase_result = next((r.get("result", "N/A") for r in result.get("results", []) if "result" in r), "N/A")
                deviation_field = "No" if xpath not in deviations else "Yes"
                platform_val = platform_support.get(xpath, "NA")
                platform_val1 = platform_val if platform_val != "NA" else "Not Applicable"
                
                result_field = ""
                if success == "FAIL":
                    if deviation_field == "Yes":
                        deviation_failures += 1
                    if deviation_field == "Yes" or platform_val in ['NS', 'NA']:
                        deviation_platform_count += 1
                        result_field = "PASS" + "(D)" + f"(P-{platform_val1})"
                    elif deviation_field == "No" and platform_val in ['S']:
                        result_field = "FAIL"
                else:
                    # The following lines seem to intend to count or adjust based on deviations,
                    # but note that adding 1 to a string is not usually the desired operation.
                    if deviation_field == 'Yes':
                        deviation_field += "1"
                    if deviation_field == "Yes" or platform_val in ['NS', 'NA']:
                        deviation_platform_count += 1   
                        result_field = "PASS" + "(D)" + f"(P-{platform_val1})"
                    else:
                        result_field = "PASS" + f"(P-{platform_val1})"

                total_validations = result.get("total_validations", 0)
                passed_validations = result.get("passed_validations", 0)
                failed_validations = result.get("failed_validations", 0)
                ignored_validations = result.get("ignored_validations", 0)
                coverage = result.get("coverage", 0)
                test_log = result.get("test_log", "N/A")
                gnmi_log = result.get("gnmi_log", "N/A")

                subscribe_field = "PASS" if result.get("success", False) else "FAIL"
                inner_logs = ""
                if success == "FAIL":
                    for inner_result in result.get("results", []):
                        log_text = inner_result.get("log", "N/A")
                        inner_logs += log_text + "<br/>"
                else:
                    inner_logs = ""

                detail_rows += f"""
                <tr>
                    <td style="text-align: right;">{s_no}</td>
                    <td>{test_id}</td>
                    <td>{testcase}</td>
                    <td>{testcase_operation}</td>   
                    <td>{success}</td>
                    <td>{deviation_field}</td>
                    <td>{platform_val1}</td>        
                    <td>{result_field}</td>
                    <td>
                        <a href="LOG_REPORT_PLACEHOLDER?test_id={unique_test_id}" onclick="openLogInNewTab(event, '{unique_test_id}', this)">{inner_logs}</a>
                </td>
                </tr>
                """
                s_no += 1
    
    elif isinstance(files, dict):
        data = files
        tests_total_validations += data.get("tests_total_validations", 0)
        tests_passed_validations += data.get("tests_passed_validations", 0)
        tests_failed_validations += data.get("tests_failed_validations", 0)
        tests_ignored_validations += data.get("tests_ignored_validations", 0)
        tests_pass += data.get("tests_pass", 0)
        tests_total += data.get("tests_total", 0)
        tests_fail += data.get("tests_fail", 0)
        
        test_target = data.get("test_target", "N/A")
        description = data.get("description", "")
        labels = data.get("labels", [])
        model_info = ", ".join(labels) if labels else "N/A"
        results = data.get("results", [])
        start_time = data.get("start_time_sec", 0)
        end_time = data.get("end_time_sec", 0)
        duration = end_time - start_time

        metadata = data.get("metadata", {})
        model_info_str.update(labels)
        model_info = ", ".join(model_info_str) if model_info_str else "N/A"
        summary = metadata.get("summary_dict", {})
        deviations = metadata.get("deviations", {})
        platform_support = metadata.get("platform_support", {})

        total_deviations += metadata.get("total_deviations", 0)
        total_paths += summary.get("total_xpaths", 0)
        set_xpaths += summary.get("set_xpaths", 0)
        state_only += summary.get("state_only", 0)
        set_get_sub += summary.get("set_get_sub", 0)
        deviations_count += summary.get("deviations", 0)
        input_xpaths += summary.get("input_xpaths", 0)
        input_state_xpaths += summary.get("input_state_xpaths", 0)
        test_set_get_sub += summary.get("test_set_get_sub", 0)
        test_state += summary.get("test_state", 0)
        test_xpaths += summary.get("test_xpaths", 0)
        test_coverage += summary.get("test_coverage", 0)

        actual_test_release_str = summary.get("actual_test_release", [])
        existing_releases = set(actual_test_release.split(", ")) if actual_test_release else set()
        if isinstance(actual_test_release_str, list):
            for release in actual_test_release_str:
                if str(release) not in existing_releases:
                    if actual_test_release:
                        actual_test_release += ", "
                    actual_test_release += str(release)
                    existing_releases.add(str(release))
        else:
            if str(actual_test_release_str) not in existing_releases:
                if actual_test_release:
                    actual_test_release += ", "
                actual_test_release += str(actual_test_release_str)
  
        test_release_str = summary.get("test_release", [])
        test_release += ", ".join(test_release_str) + ", " if isinstance(test_release_str, list) else str(test_release_str) + ", "
        test_platform_str = summary.get("test_platform", [])
        if isinstance(test_platform_str, list):
            if test_platform:
                test_platform += " ab"
            test_platform += ", ".join(test_platform_str)
        else:
            if test_platform:
                test_platform += "cd "
            test_platform += str(test_platform_str)
            
        platform_support_summary_str = summary.get("platform_support", [])
        existing_platform_supports = set(platform_support_summary.split(", ")) if platform_support_summary else set()
        if isinstance(platform_support_summary_str, list):
            for platform in platform_support_summary_str:
                if str(platform) not in existing_platform_supports:
                    if platform_support_summary:
                        platform_support_summary += ", "
                    platform_support_summary += str(platform)
                    existing_platform_supports.add(str(platform))
        else:
            if str(platform_support_summary_str) not in existing_platform_supports:
                if platform_support_summary:
                    platform_support_summary += ", "
                platform_support_summary += str(platform_support_summary_str)

        test_coverage_str = f"{test_coverage}% [{input_xpaths}/{total_paths}]"
        detail_rows = ""
        s_no = 1
        test_id_counter = {}
        for result in sorted(results, key=lambda r: int(re.findall(r'\d+', r.get("test_id", "0"))[0])):
            test_id = result.get("test_id", "")
            # New unique key generation using a counter
            current_count = test_id_counter.get(test_id, 0) + 1
            test_id_counter[test_id] = current_count
            unique_test_id = test_id if current_count == 1 else f"{test_id}_{current_count}"
            
            testcase = result.get("test_name", "")
            if "<-" in testcase and "->" in testcase:
                before = testcase.split("<-")[0].strip()
                bold_part = testcase.split("<-")[1].split("->")[0].strip()
                after = testcase.split("->")[1].strip()
                testcase = f'{before} <- <b>{bold_part}</b> -> {after}'
            inner_results = result.get("results", [])
            if inner_results:
                validations = inner_results[0].get("validations", {})
                op_dict = validations.get("Set_and_Get", {}).get("type", {})
                if op_dict:
                    op_type = list(op_dict.keys())[0]
                    testcase_operation = "SET - " + op_type + " & GET" if op_type == "UPDATE" else "SET - " + op_type
                else:
                    testcase_operation = testcase.split("<-")[0].strip() if "<-" in testcase else testcase
            else:
                testcase_operation = testcase.split("<-")[0].strip() if "<-" in testcase else testcase

            test_id = result.get("test_id", "")
            xpath = extract_xpath(testcase)
            success = "PASS" if result.get("success", False) else "FAIL"
            testcase_result = next((r.get("result", "N/A") for r in result.get("results", []) if "result" in r), "N/A")
            deviation_field = "No" if xpath not in deviations else "Yes"
            platform_val = platform_support.get(xpath, "NA")
            platform_val1 = platform_val if platform_val != "NA" else "Not Applicable"
            
            result_field = ""
            if success == "FAIL":
                if deviation_field == 'Yes':
                    deviation_field += "1"
                if deviation_field == "Yes" or platform_val in ['NS', 'NA']:  
                    result_field = "PASS" + "(D)" + f"(P-{platform_val1})"
                elif deviation_field == "No" and platform_val in ['S']:
                    result_field = "FAIL"
            else:
                if deviation_field == 'Yes':
                    deviation_field += "1"
                if deviation_field == "Yes" or platform_val in ['NS', 'NA']:  
                    result_field = "PASS" + "(D)" + f"(P-{platform_val1})"
                else:
                    result_field = "PASS" + f"(P-{platform_val1})"

            total_validations = result.get("total_validations", 0)
            passed_validations = result.get("passed_validations", 0)
            failed_validations = result.get("failed_validations", 0)
            ignored_validations = result.get("ignored_validations", 0)
            coverage = result.get("coverage", 0)
            test_log = result.get("test_log", "N/A")
            gnmi_log = result.get("gnmi_log", "N/A")

            subscribe_field = "PASS" if result.get("success", False) else "FAIL"
            inner_logs = ""
            if success == "FAIL":
                for inner_result in result.get("results", []):
                    log_text = inner_result.get("log", "N/A")
                    inner_logs += log_text + "<br/>"
            else:
                inner_logs = ""
            detail_rows += f"""
            <tr>
            <td style="text-align: right;">{s_no}</td>
            <td>{test_id}</td>
            <td>{testcase}</td>
            <td>{testcase_operation}</td>
            <td>{success}</td>
            <td>{deviation_field}</td>
            <td>{platform_val1}</td>
            <td>{result_field}</td>
             <td> <a href="javascript:void(0)" onclick='parent.postMessage({{"action": "navigateToLogReport", "testId": "{unique_test_id}"}}, "*");'>{inner_logs}</a></td>
            </tr>
            """
            s_no += 1

    test_platform_str = test_platform
    base_dir = os.path.dirname(os.path.abspath(__file__))
    alternative_template_path = os.path.join("Report_Generators/Testcase_Report_HTML/template.html")
    main_template_path = os.path.join("template.html")
    template_path = alternative_template_path if os.path.exists(alternative_template_path) else main_template_path

    with open(template_path, "r", encoding="utf-8") as f:
        template_html = f.read()

    template_html = template_html.replace("xpath_model_info", str(model_info))
    template_html = template_html.replace("xpath_total_paths", str(total_paths))
    template_html = template_html.replace("xpath_config_paths", str(set_xpaths))
    template_html = template_html.replace("xpath_set_get_sub", str(test_set_get_sub))
    template_html = template_html.replace("xpath_state_only", str(state_only))
    template_html = template_html.replace("xpath_deviations", str(total_deviations))
    template_html = template_html.replace("xpath_p_result", str(test_platform_str))
    template_html = template_html.replace(
        "xpath_platform",
        f"Tagged : {test_platform}: {test_platform} - {input_xpaths}/{total_paths}"
    )
    template_html = template_html.replace("xpath_test_release", str(actual_test_release))
    template_html = template_html.replace("xpath_platform_support", str(platform_support_summary))
    template_html = template_html.replace("xpath_tested_paths", str(test_xpaths))
    template_html = template_html.replace("xpath_input_config", str(input_xpaths))
    template_html = template_html.replace("xpath_tested_set_get_sub", str(test_set_get_sub))
    template_html = template_html.replace("xpath_tested_state_only", str(state_only))
    template_html = template_html.replace("xpath_test_coverage", str(test_coverage_str))
    template_html = template_html.replace("xpath_total_testcases", str(tests_total))
    template_html = template_html.replace("xpath_passed", str(tests_pass))
    template_html = template_html.replace("xpath_failed", f"{tests_fail} [F - {abs(tests_fail - deviation_failures)} D/P/S - {deviation_failures}]")
    template_html = template_html.replace(
            "xpath_overall_result",
            "PASS" if deviation_failures > 0 else "FAIL")
    template_html = template_html.replace("<!-- xpath_detail_rows -->", detail_rows)

    output_folder = "logs"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, output_folder)
    os.makedirs(logs_dir, exist_ok=True)

    output_path = os.path.join(logs_dir, filename_result + "_testcase_report" + ".html")
    with open(output_path, "w", encoding="utf-8") as out_file:
        out_file.write(template_html)

    print(f"Generated HTML report at: {os.path.abspath(output_path)}")

import os
import sys
import json

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_test_result.py <json_file1> <json_file2> ... OR <json_directory>")
        sys.exit(1)

    input_paths = sys.argv[1:]

    if len(input_paths) == 1 and os.path.isdir(input_paths[0]):
        input_path = input_paths[0]
        print(f"📁 Handling directory: {input_path}")
        filename_result = os.path.basename(os.path.normpath(input_path))
        data = parse_log_files_from_directory(input_path)
        dict_data_handling(data, filename_result)
        return

    combined_data = []
    valid_files = []

    for path in input_paths:
        if os.path.isfile(path) and path.endswith("_result.json"):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        combined_data.extend(data)
                    elif isinstance(data, dict):
                        combined_data.append(data)
                    else:
                        print(f"⚠️ Skipping invalid format in: {path}")
                valid_files.append(path)
            except Exception as e:
                print(f"❌ Error reading {path}: {e}")
                sys.exit(1)
        else:
            print(f"❌ Invalid input: {path} (must be a .json file ending with _result.json)")
            sys.exit(1)

    if not valid_files:
        print("❌ No valid JSON files found.")
        sys.exit(1)

    with open("combined_data.json", 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=4)
    print("✅ Combined data saved to combined_data.json")

    filename_result = "_".join([
        os.path.splitext(os.path.basename(p))[0].replace("_result", "") 
        for p in valid_files
    ])

    print(f"✅ Prefix used: {filename_result}")
    dict_data_handling(combined_data, filename_result)

if __name__ == "__main__":
    main()
