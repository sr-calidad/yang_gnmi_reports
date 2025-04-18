import os
import sys
import glob
import shutil
import subprocess
import argparse

def run_report_script(script_path, args_list):
    # cmd = [sys.executable, script_path] + args_list
    # subprocess.run(cmd, check=True)
    cmd = [sys.executable, script_path] + args_list
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        error_message = str(e)
        if "No valid JSON files found" in error_message:
            print("Error: JSON file not found. Please ensure the JSON file exists in the specified directory.")
        # else:
        #     print(f"Error executing script '{script_path}': {e}")
        sys.exit(1)

def get_latest_html_report(directory):
    html_files = glob.glob(os.path.join(directory, "*.html"))
    if not html_files:
        sys.exit(f"No HTML files found in {directory}")
    return max(html_files, key=os.path.getctime)

import os
import html

def combine_reports(log_report, testcase_report, yang_report, output_file):
    # Read the content of each HTML report.
    with open(log_report, "r", encoding="utf-8") as f:
        log_content = f.read()
    with open(testcase_report, "r", encoding="utf-8") as f:
        testcase_content = f.read()
    with open(yang_report, "r", encoding="utf-8") as f:
        yang_content = f.read()
    
    global_output_folder = os.path.dirname(os.path.abspath(output_file))
    relative_log_report_path = os.path.relpath(log_report, global_output_folder)
    updated_testcase_content = testcase_content.replace("LOG_REPORT_PLACEHOLDER", relative_log_report_path)
   
    # Escape content so it can be safely embedded in the srcdoc attribute.
    encoded_log = html.escape(log_content, quote=True)
    encoded_testcase = html.escape(updated_testcase_content, quote=True)
    encoded_yang = html.escape(yang_content, quote=True)

    # Create the consolidated HTML with navigation and iframes using srcdoc.
    combined_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Standalone Consolidated Test Report</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
    }}
    #fixedHeader {{
      position: fixed;
      top: 0;
      left: -10px;
      width: 100%;
      background-color: rgba(176, 171, 171, 0.9);
      padding: 5px;
      display: flex;
      justify-content: right;
      gap: 6px;
      z-index: 1000;
    }}
    .nav-button {{
      background-color: #ddd;
      border: none;
      padding: 7px 20px;
      cursor: pointer;
      font-size: 14px;
      border-radius: 8px;
      font-weight: bold;
    }}
    .nav-button:hover {{
      background-color: #777;
    }}
    .section {{
      display: none;
      padding-top: 40px; /* leave room for fixed header */
      height: calc(100vh - 60px);
    }}
    .active {{
      display: block;
    }}
    iframe {{
      width: 100%;
      height: 100%;
      border: none;
    }}
  </style>
  <script>
  function showSection(id) {{
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
  }}

  window.onload = function() {{
    // 0) Nuke any “#…” in the URL so the browser can’t auto‑jump
    if (window.location.hash) {{
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }}
    // 1) Force the parent back to the very top
    window.scrollTo(0, 0);

    const params = new URLSearchParams(window.location.search);
    const testId = params.get('test_id');

    if (testId) {{
      // 2) Show the Log Report
      showSection('log_section');

      // 3) Drill into the iframe and highlight + scroll
      const frame = document.querySelector('#log_section iframe');
      const doc   = frame.contentDocument || frame.contentWindow.document;

      const leftLi = doc.querySelector(`#testcase-list li[data-tc="${{testId}}"]`);
      const target = doc.getElementById('testcase-' + testId);

      if (leftLi && target) {{
        // clear old
        doc.querySelectorAll('#testcase-list li.active, #logContent > div.active')
           .forEach(el => el.classList.remove('active'));

        leftLi.classList.add('active');
        target.classList.add('active');

        // scroll the left list
        doc.querySelector('#left-panel .card-body')
           .scrollTop = leftLi.offsetTop - 100;

        // INSTANT jump in the right panel (no smooth)
        const rightContainer = doc.getElementById('rightPanelBody');
        rightContainer.scrollTop = target.offsetTop - 60;
      }}
    }} else {{
      // default: Testcase tab
      showSection('testcase_section');
    }}

  }};
</script>




</head>
<body>
  <div id="fixedHeader">
    <button class="nav-button" onclick="showSection('testcase_section')">Testcase Report</button>
    <button class="nav-button" onclick="showSection('log_section')">Log Report</button>
    <button class="nav-button" onclick="showSection('yang_section')">Yang Tree Report</button>
  </div>
  <div id="log_section" class="section">
    <iframe srcdoc="{encoded_log}"></iframe>
  </div>
  <div id="testcase_section" class="section">
    <iframe srcdoc="{encoded_testcase}"></iframe>
  </div>
  <div id="yang_section" class="section">
    <iframe srcdoc="{encoded_yang}"></iframe>
  </div>
</body>
</html>
"""

    # Write the self-contained consolidated report.
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_html)
    print("Standalone consolidated report generated at:", output_file)



def main():
    parser = argparse.ArgumentParser(
        description="Generate consolidated test report from log, JSON, and YAML inputs."
    )
    parser.add_argument("--dir", help="Directory containing the log, JSON, and YAML files")
    parser.add_argument("--log", help="Path to the log file")
    parser.add_argument("--json", help="Path to the JSON file")
    parser.add_argument("--yaml", help="Path to the YAML file")
    args = parser.parse_args()

    # Determine mode.
    if args.log and args.json and args.yaml:
        mode = "individual"
    elif args.dir:
        mode = "directory"
    else:
        sys.exit("Error: Provide either --dir or all of --log, --json, and --yaml.")

    if mode == "directory":
        base_dir = os.path.abspath(args.dir)
        output_prefix = os.path.basename(os.path.normpath(base_dir))
        log_prefix = output_prefix
        other_prefix = output_prefix
    else:
        base_dir = os.path.dirname(os.path.abspath(args.json))
        log_prefix = os.path.splitext(os.path.basename(os.path.abspath(args.log)))[0]
        other_prefix = os.path.splitext(os.path.basename(os.path.abspath(args.json)))[0]
        output_prefix = other_prefix

    print("Using base directory:", base_dir)
    if mode == "individual":
        print("Log file:", os.path.abspath(args.log))
        print("JSON file:", os.path.abspath(args.json))
        print("YAML file:", os.path.abspath(args.yaml))

  

    # -------------------------------
    # Generate Log Report
    # -------------------------------
    log_script = os.path.join("Report_Generators", "TC_Log_HTML", "process_log.py")
    if mode == "directory":
        run_report_script(log_script, [base_dir])
    else:
        run_report_script(log_script, [os.path.dirname(os.path.abspath(args.log))])
    
    log_reports_dir = os.path.join(os.getcwd(), "Report_Generators", "TC_Log_HTML", "logs")
    latest_log_report = get_latest_html_report(log_reports_dir)
    final_log_report = os.path.join(log_reports_dir, f"{log_prefix}_report.html")
    if os.path.abspath(latest_log_report) != os.path.abspath(final_log_report):
        if os.path.exists(final_log_report):
            os.remove(final_log_report)
        os.rename(latest_log_report, final_log_report)
    print("Log report available at:", final_log_report)

    # -------------------------------
    # Generate Testcase Report
    # -------------------------------
    testcase_script = os.path.join("Report_Generators", "Testcase_Report_HTML", "generate_test_result1.py")
    if mode == "directory":
         testcase_arg = base_dir
    else:
         testcase_arg = os.path.abspath(args.json)
    run_report_script(testcase_script, [testcase_arg])
    testcase_reports_dir = os.path.join(os.getcwd(), "Report_Generators", "Testcase_Report_HTML", "logs")
    latest_testcase_report = get_latest_html_report(testcase_reports_dir)
    final_testcase_report = os.path.join(testcase_reports_dir, f"{other_prefix}_testcase_report.html")
    if os.path.abspath(latest_testcase_report) != os.path.abspath(final_testcase_report):
        if os.path.exists(final_testcase_report):
            os.remove(final_testcase_report)
        os.rename(latest_testcase_report, final_testcase_report)
    print("Testcase report available at:", final_testcase_report)

    # -------------------------------
    # Generate Yang Tree Report
    # -------------------------------
    yang_script = os.path.join("Report_Generators", "Yang_Tree_HTML", "generate_html.py")
    
    if mode == "directory":
        # In directory mode we use a fixed YAML file and pass the entire directory so that
        # the yang generator processes every file.
        fixed_yaml = os.path.join("Report_Generators", "Yang_Tree_HTML", "validation.yaml")
        run_report_script(yang_script, [fixed_yaml, base_dir])
    else:
        yaml_file = os.path.abspath(args.yaml)
        json_file = os.path.abspath(args.json)
        run_report_script(yang_script, [yaml_file, os.path.dirname(json_file)])
    
    yang_reports_dir = os.path.join(os.getcwd(), "Report_Generators", "Yang_Tree_HTML", "logs")
    latest_yang_report = get_latest_html_report(yang_reports_dir)
    final_yang_report = os.path.join(yang_reports_dir, f"{other_prefix}_yang_report.html")
    if os.path.abspath(latest_yang_report) != os.path.abspath(final_yang_report):
        if os.path.exists(final_yang_report):
            os.remove(final_yang_report)
        os.rename(latest_yang_report, final_yang_report)
    print("Yang Tree report available at:", final_yang_report)

    # -------------------------------
    # Generate Consolidated Report
    # -------------------------------
    global_output_folder = os.path.join(os.getcwd(), "logs")
    os.makedirs(global_output_folder, exist_ok=True)
    consolidated_report = os.path.join(global_output_folder, f"{other_prefix}_consolidated_report.html")
    combine_reports(final_log_report, final_testcase_report, final_yang_report, consolidated_report)

if __name__ == "__main__":
    main()
