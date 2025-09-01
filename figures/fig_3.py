import json
import matplotlib.pyplot as plt

with open('research_results_20250824_192037.json', 'r') as file:
    data = json.load(file)

dat = [0, 0, 0]

for entry in data["results"]:
    task_name = entry.get("task_id")
    if "tle_analysis" in entry:
        dat[0] += entry["tle_analysis"]["total_input_sizes"]
        dat[1] += entry["tle_analysis"]["tle_count"]
        dat[2] += entry["mle_analysis"]["mle_count"]

plt.xlabel("Result Type")
plt.ylabel("Count")
plt.title("Result Types for Each Testcase")

plt.bar(["Total", "TLE Count", "MLE Count"], dat)

plt.savefig('fig_3.png', bbox_inches='tight')
