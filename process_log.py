# Run this code from /var/www/html/aish/api-publish/tools/yang_gnmi_validator OR
# from /var/www/html/aish/api-publish/tools/yang_gnmi_validator/Report_Generators/TC_Log_HTML
# Report will be generated at /var/www/html/aish/api-publish/tools/yang_gnmi_validator/
import sys
import re
import json
import os
import html

def remove_border_lines(ascii_block):
    lines = ascii_block.strip().split("\n")
    return [
        line.strip()
        for line in lines
        if not re.match(r"^\+\s*(?:-+\s*\+)+$", line.strip())
    ]

def extract_ascii_rows(lines):
    rows = [line.strip("|").split("|") for line in lines if line.startswith("|")]
    return [[cell.strip() for cell in row] for row in rows]

def normalize_rows(rows):
    if not rows:
        return rows

    max_cols = max(len(row) for row in rows)
    for row in rows:
        if len(row) < max_cols:
            row.extend([""] * (max_cols - len(row)))

    non_empty_indices = [i for i in range(max_cols) if any(row[i] for row in rows)]
    return [[row[i] for i in non_empty_indices] for row in rows]

def build_table_html(rows):
    table_html = (
        "<table class='ascii-table' border='1' cellpadding='5' cellspacing='0' "
        "style='border-collapse: collapse; width: auto; text-align: left;'>"
        "<tbody>"
    )
    for row in rows:
        table_html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
    table_html += "</tbody></table>"
    return table_html

def build_collapsible_section(title, content, after=""):
    return (
        f'\n<details class="collapsible-section">'
        f'\n<summary class="collapsible-summary"><b>{title}</b></summary>'
        f'\n<div class="collapsible-box" style="border: 1px solid #ccc; padding: 10px; background-color: #f9f9f9;">'
        f'\n{content}\n</div>\n</details>\n{after}'
    )


def clean_ascii_table(ascii_block):
    cleaned_lines = remove_border_lines(ascii_block)
    rows = extract_ascii_rows(cleaned_lines)
    if not rows:
        return ascii_block

    all_subtables = []
    current_table = []
    prev_cols = None

    for row in rows:
        num_cols = len(row)
        if prev_cols is not None and num_cols != prev_cols:
            all_subtables.append(current_table)
            current_table = [row]
        else:
            current_table.append(row)
        prev_cols = num_cols

    if current_table:
        all_subtables.append(current_table)

    final_html_chunks = []
    for subtable_rows in all_subtables:
        subtable_rows = [r for r in subtable_rows if any(cell for cell in r)]
        if not subtable_rows:
            continue

        subtable_rows = normalize_rows(subtable_rows)
        table_html = build_table_html(subtable_rows)
        final_html_chunks.append(table_html)

    return "<br>".join(final_html_chunks)

def clean_failed_validation_table(ascii_block):
    ascii_block = "\n".join(
        line for line in ascii_block.splitlines()
        if not (re.search(r"-{5,}", line) and not re.search(r"[A-Za-z0-9]", line))
    )

    cleaned_lines = remove_border_lines(ascii_block)
    rows = extract_ascii_rows(cleaned_lines)

    merged_rows = []
    for row in rows:
        if merged_rows and row and row[0] == "":
            for i, cell in enumerate(row):
                if cell:
                    if i < len(merged_rows[-1]):
                        merged_rows[-1][i] += " " + cell
                    else:
                        merged_rows[-1].append(cell)
        else:
            merged_rows.append(row)
    rows = merged_rows

    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return ascii_block

    rows = normalize_rows(rows)
    return build_table_html(rows)

def convert_section_to_html(title, content):
    content = content.strip()
    converted_content = re.sub(
        r'((?:\A|(?<=\n))(?:[+|].*(?:\n|$))+)',
        lambda m: clean_ascii_table(m.group(1)),
        content,
        flags=re.MULTILINE
    )
    return build_collapsible_section(title, converted_content)


def convert_failed_validations_to_html(match):
    header_text = "View Failed Validations"
    ascii_block = match.group(2)
    converted_table = clean_failed_validation_table(ascii_block)
    return build_collapsible_section(
        header_text,
        converted_table,
        after='<br><div style="margin-top: 15px; clear: both;"></div>'
    )

def convert_validating_eom_sections(text):
    pattern = re.compile(
        r"(\+[-]+?\+\s*\n\|\s*(Validating EOM, Frequency & Timestamps for -.*)\s*\|\s*\n\+[-]+?\+)"  # Header
        r"([\s\S]+?)(?="
        r"(?:\n\+[-]+?\+\s*\n\|\s*Validating EOM, Frequency & Timestamps for -|"
        r"\n\+[-]+?\+\s*\n\|\s*TESTCASE RESULT|"
        r"\n\|\s*Step\s*\d+:|"  # Add check for Step headers
        r"\n\+[-]+?\+\s*\n\|\s*Time Intervals\s*\||"
        r"\n<details\s+class=\"collapsible-section\">|"
        r"\Z))",  # Updated lookahead
        flags=re.MULTILINE
    )
    def replacer(m):
        summary_text = m.group(2).strip()
        content = m.group(3)
        return (
            f'<details class="collapsible-section">'
            f'<summary class="collapsible-summary"><b>{summary_text}</b></summary>'
            f'<div class="collapsible-box">{content}</div>'
            f'</details>'
        )

    old_text = None
    while old_text != text:
        old_text = text
        text = pattern.sub(replacer, text)
    return text

def highlight_testcase_result(match, tc_id):
    original_text = match.group(0)
    result_label = match.group(1)
    result_text = match.group(2)

    color = "green" if result_text == "PASS" else "red"

    if result_text == "PASS":
        # Check for context in the full match
        if "[Operation FAIL" in original_text:
            color = "orange"
        elif "[Operation PASS" in original_text:
            color = "#1e79ff"

    highlighted_result = f'<span style="color: {color}; font-weight: bold;">{html.escape(original_text)}</span>'
    colored_tc_id = f'<span style="color: {color}; font-weight: bold;">{html.escape(tc_id)}</span>'
    return highlighted_result, colored_tc_id,color




# This will be used to replace the result and color the TC_ID
def inject_result(match, tc_id):
    result_html, colored_tc_id,color = highlight_testcase_result(match, tc_id)
    # You can return only result_html here
    return result_html


def parse_log_content(content):
    testcases = re.split(r"\[TESTCASE-BEGIN\]", content)
    testcase_data = {}

    for testcase in testcases:
        if not testcase.strip():
            continue

        tc_id_match = re.search(r"(TC_\d+)", testcase)
        if not tc_id_match:
            continue
        tc_id = tc_id_match.group(1)

        # Extract Testcase Result (PASS/FAIL) from the raw testcase content
        result_match = re.search(r"(TESTCASE RESULT\s*-\s*)(PASS|FAIL)(\s*\[.*?\])?", testcase, re.IGNORECASE)
        result_text = result_match.group(2).upper() if result_match else "UNKNOWN"
        original_text = result_match.group(3) if result_match and result_match.group(3) != None else ""
        print(result_text, original_text)
        if result_text == "PASS":
            # Check for context in the full match
            if "[Operation FAIL" in original_text:
                status_class = "promoted_pass"
            elif "[Operation PASS" in original_text:
                status_class = "anomaly_pass"
            else:
                status_class = "pass"
        else:
            status_class = "fail"

        #status_class = "pass" if result_text == "PASS" else "fail"
        color = "green" if result_text == "PASS" else "red"

        # Build colored TC_ID without adding duplicate text—just modify the existing one.
        colored_tc_id = f'<span style="color: {color}; font-weight: bold;">{tc_id}</span>'

        # Replace only the first occurrence of the TC_ID (as a whole word) in the testcase content
        processed_testcase = re.sub(r'\b' + re.escape(tc_id) + r'\b', colored_tc_id, testcase, count=1)


        processed_testcase = re.sub(
            r"(\[GNMI RESPONSE\][\s\S]*?\[End of GNMI RESPONSE\]\n?)",
            lambda m: (
                f'<details class="collapsible-section">'
                f'<summary class="collapsible-summary"><b>View GNMI Response</b></summary>'
                f'<div class="collapsible-box" style="position: relative; padding: 10px; max-height: 500px; overflow-y: auto; border: 1px solid #ccc; display: flex; flex-direction: column;">'
                
                # Sticky button container
                f'<div style="position: sticky; top: 0; right: 0; background: white; display: flex; justify-content: flex-end; padding: 5px; z-index: 1000;">'
                f'<button class="expand-button" '
                f'style="background: #99a2ac; color: white; border: none; padding: 5px 10px; cursor: pointer; font-size: 0.9rem; border-radius: 4px;" '
                f'onclick="openGNMIResponseInNewTab(\'gnmi_response_{tc_id}\')">Expand View</button>'
                f'</div>'

                # Preformatted text area (response content)
                f'<pre id="gnmi_response_{tc_id}" style="white-space: pre-wrap; word-wrap: break-word; margin: 0;">{html.escape(m.group(1))}</pre>'
                
                f'</div>'
                f'</details>'
            ),
            testcase
        )

        processed_testcase = re.sub(
            r"(\+\-+\+\s*\n\|\s*VALIDATIONS[^\n]*\|\s*\n\+\-+\+\s*\n)([\s\S]+?)(?=\n\+\-+\+\s*\n|\Z)",
            lambda m: convert_section_to_html("View Validations", m.group(2).strip()),
            processed_testcase,
            flags=re.MULTILINE | re.DOTALL
        )
        # In the convert_validating_eom_sections function, modify the regex pattern
        processed_testcase = re.sub(
            r"(\+[-]+\+\s*\n\|\s*(🛠\s+Manual Repro Info:.*?)\s*\|\s*\n\+[-]+\+\s*\n)"  # Header with 🛠
            r"([\s\S]*?)\n?\[END OF REPRO-INFO\]\n?",  # Content until END marker
            lambda m: convert_section_to_html(m.group(2).strip(), m.group(3).strip()),  
            processed_testcase,
            flags=re.MULTILINE | re.DOTALL
        )

        #working code
        processed_testcase = re.sub(
                r"(\+[-]+?\+\s*\| Coverage Mismatch Details \|\s*\+[-]+?\+\n)",
                lambda m: convert_section_to_html("View Coverage Mismatch Details", ""),
                processed_testcase,
                flags=re.MULTILINE
            )

        processed_testcase = re.sub(
            r"(\+[-]+?\+\s*\| Additional Paths Found in update that are not defined in schema.*?\|\s*\+[-]+?\+\n)"
            r"([\s\S]+?)(?=(?:\n\+[-]+\+\s*\n\| Step|\n\+[-]+\+\s*\| TESTCASE RESULT|\[TESTCASE-BEGIN\]|\Z))",
            lambda m: convert_section_to_html("View Additional Paths Found", clean_ascii_table(m.group(2))),
            processed_testcase,
            flags=re.MULTILINE | re.DOTALL
        )

        # ✅ Colorize TESTCASE RESULT - PASS (Green) / FAIL (Red)
        processed_testcase = re.sub(
            r"(TESTCASE RESULT\s*-\s*)(PASS|FAIL)(?:\s*\[.*?\])?",
            lambda match: inject_result(match, tc_id),
            processed_testcase,
            flags=re.MULTILINE
        )

        processed_testcase = re.sub(
            r"(FAILED VALIDATIONS:\n)((?:[+|].*(?:\n|$))+)",
            lambda m: convert_failed_validations_to_html(m),
            processed_testcase,
            flags=re.MULTILINE
        )

        processed_testcase = re.sub(
            r"((?:\+[-]+\+\s*\n\|\s*Sample-Interval:.*\n\+[-]+\+\n)(?:[+|].*\n)+)",
            lambda m: build_collapsible_section(
                "View Sample Interval Details",
                clean_ascii_table(m.group(1))
            ),
            processed_testcase,
            flags=re.MULTILINE
        )
        processed_testcase = re.sub(
            r"(\+\-+\+\s*\n\|\s*Time Intervals\s*\|\s*\n\+\-+\+\n)"
            r"([\s\S]+?)(?=(?:\+\-+\+\s*\n\|\s*Time Intervals\s*\||"
            r"\n\+[-]+\+\s*\n\|\s*Step\s*\d+:|"  # Step headers
            r"\n\|\s*VALIDATIONS|\| Sample-Interval|"
            r"\n\|\s*Validating EOM, Frequency & Timestamps for -|"  # NEW STOP CONDITION
            r"\n\[TESTCASE-BEGIN\]|\Z))",  # Existing conditions
            lambda m: build_collapsible_section(
                "View Time Intervals Details",
                clean_ascii_table(m.group(1)) + clean_ascii_table(m.group(2))),
            processed_testcase,
            flags=re.MULTILINE | re.DOTALL
        )
        processed_testcase = re.sub(
            r"(\[RPC\][\s\S]*?)\n?\[END OF RPC\]\n?", 
            lambda m: convert_section_to_html("View RPC", m.group(1).strip()),  
            processed_testcase,
            flags=re.MULTILINE | re.DOTALL
        )

        processed_testcase = convert_validating_eom_sections(processed_testcase)

        processed_testcase = re.sub(
            r"(\+[-]+\+\n\|\s*(Step\s*\d+:.*?)\s*\|\n\+[-]+\+\n)((?:\|.*?\n)*?)\+[-]+\+\n",
            lambda m: (lambda rows: convert_section_to_html(
                m.group(2),  # Use actual step title (e.g., "Step 1: 🚀 Initiating GNMI Set... - (🔍 Assessment Step)")
                "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])  # Convert step table to collapsible format
            ))(extract_ascii_rows(remove_border_lines(m.group(3)))),
            processed_testcase,
            flags=re.MULTILINE | re.DOTALL
        )

        processed_testcase = re.sub(
            r'((?:\A|(?<=\n))(?:[+|].*(?:\n|$))+)',
            lambda m: clean_ascii_table(m.group(1)),
            processed_testcase,
            flags=re.MULTILINE
        )

        final_html = (
            f'<div id="{tc_id}" class="testcase-section" data-status="{status_class}" data-color="{color}">'
            f'<br>{processed_testcase}</div>'
        )
     
         # Ensure the key is unique if duplicate TC_ID exists
        unique_key = tc_id
        counter = 0
        while unique_key in testcase_data:
            counter += 1
            unique_key = f"{tc_id}_{counter}"
        testcase_data[unique_key] = final_html

    return {"testcase_data": testcase_data}

def parse_log_files_from_directory(directory):
    combined_content = ""
    model_info =""
    for filename in os.listdir(directory):
        if filename.endswith("-tc_result.log"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    combined_content += content
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                continue
        if filename.endswith("_result.json"):
            filepath_json = os.path.join(directory, filename)
            try:
                with open(filepath_json, 'r', encoding='utf-8') as f:
                    content_json = f.read()
                    parsed_json = json.loads(content_json)
                    model_info = parsed_json['labels'][0]
                    model_info = model_info.replace('_', '-').title() if model_info else ""
            except Exception as e:
                print(f"Error reaeding file {filename}: {e}")
                continue

    return combined_content,model_info

def generate_html(data, input_path,model_info, output_folder="logs"):
    # Determine the base directory of the script (2 levels up if inside Report_Generators)
    base_dir = os.path.dirname(os.path.abspath(__file__)) #replaced with abover line 
    logs_dir = os.path.join(base_dir, "logs")#replaced with abover line 
    os.makedirs(logs_dir, exist_ok=True)


    if os.path.isfile(input_path): # Single file
       # Extract the base name of the input file without the extension
        file_name_without_extension = os.path.splitext(os.path.basename(input_path))[0]
        base_name =  f"{file_name_without_extension}_log_report.html"
    else: # Directory, combined report
        base_name = os.path.basename(os.path.normpath(input_path))+ "_log_report.html"

    # output_file = os.path.join(base_dir,output_folder, base_name) #Output the file
    output_file = os.path.join(logs_dir, base_name)#replaced with above line 


        # Determine the base directory of the script
    base_dir = os.path.dirname(os.path.abspath(__file__))

        # Set the template path dynamically
    alternative_template_path = os.path.join("Report_Generators/TC_Log_HTML/processed_log_template.html")
        # OR if the file is in the current directory
    main_template_path = os.path.join("processed_log_template.html")

    if os.path.exists(alternative_template_path):
        template_path = alternative_template_path
    else:
        template_path = main_template_path

    # template_path = "Report_Generators/TC_Log_HTML/processed_log_template.html"
    with open(template_path, 'r', encoding='utf-8') as template_file:
        template_content = template_file.read()

    all_testcases = "\n".join(data["testcase_data"].values())
    rendered_html = template_content.replace("{{testcase_data}}", json.dumps(data["testcase_data"]))
    rendered_html = rendered_html.replace("{{all_testcases}}", all_testcases)
    rendered_html = rendered_html.replace("{{model_info}}", json.dumps(model_info if model_info else ""))
    rendered_html = rendered_html.replace("{{model_info_raw}}", model_info if model_info else "")
    model_heading = f'<span style="font-size:14px; margin:0 5px;">&#9654;</span>Model : {model_info}' if model_info else ''
    rendered_html = rendered_html.replace("{{model_heading}}", model_heading)

    with open(output_file, 'w', encoding='utf-8',errors='ignore') as f:
        f.write(rendered_html)

    return output_file

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_log.py <log_file or directory>")
        sys.exit(1)

    input_path = sys.argv[1]
    model_info =""

    try:
        if os.path.isfile(input_path) and input_path.endswith("-tc_result.log"):
            with open(input_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            parsed_data = parse_log_content(log_content)
        elif os.path.isdir(input_path):

            combined_log_content,model_info = parse_log_files_from_directory(input_path)
            parsed_data = parse_log_content(combined_log_content)
        else:
            print(f"Error: '{input_path}' is not a valid log file or directory.")
            sys.exit(1)

        output_file = generate_html(parsed_data, input_path,model_info)
        print(f"✅ HTML report generated: {output_file}")
    except Exception as e:
        print(f"❌ Error processing the log file: {e}")
        import traceback
        traceback.print_exc()
