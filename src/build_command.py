import yaml
import json
import os
import base64

# Read the YAML file and convert it to JSON
yaml_file_path = os.path.join(os.getenv('MATRIX_FOLDER'), 'rover.yaml')
with open(yaml_file_path, 'r') as f:
    yaml_content = yaml.safe_load(f)

json_content = json.dumps(yaml_content['rover'])
print(f"JSON: {json_content}")  # Debugging line

# Initialize the rover command
output = "/tf/rover/rover.sh \\"

# Parse the JSON to build the command
for key, value in json.loads(json_content).items():
    print(f"Key: {key}, Value: {value}")  # Debugging line
    output += "\n"  # Newline

    if key == "impersonate-sp-from-keyvault-url" and value != "null":
        output += f"--{key} {value} \\"
        continue

    if key in ["a", "p"] or value in ["apply", "plan", "destroy"]:
        continue

    if key == "tfstate" and value != "null":
        output += f" -{key} {value} \\"
        os.environ['tfstate'] = value
        continue

    if key in ["lz", "landingzone"]:
        output += f" -{key} {os.getenv('GITHUB_WORKSPACE')}/{value} \\"
        continue

    if key == "var-folder":
        output += f" -{key} {os.getenv('GITHUB_WORKSPACE')}/{value} \\"
        continue

    output += f" -{key}"
    if value != "null":
        output += f" {value} \\"
    else:
        output += " \\"

print(output)

# Encode the rover command
rover_cmd_encoded = base64.b64encode(output.encode()).decode()
print(f"rover_cmd_encoded: {rover_cmd_encoded}")
os.environ['rover_cmd_encoded'] = rover_cmd_encoded

# Create variables for plan and output files
plan_file = f"{os.getenv('RUNNER_TEMP')}/{os.getenv('GITHUB_RUN_ID')}_{os.getenv('tfstate')}.tfplan"
print(f"plan_file: {plan_file}")
os.environ['plan_file'] = plan_file

output_file = f"{os.getenv('RUNNER_TEMP')}/{os.getenv('GITHUB_RUN_ID')}_{os.getenv('tfstate')}.tfplan.output"
print(f"output_file: {output_file}")
os.environ['output_file'] = output_file
