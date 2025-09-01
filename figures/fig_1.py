import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator

# Load the JSON file
with open("research_results_20250824_192037.json", "r") as f:
    data = json.load(f)

# Separate durations by task type
bigobench_durations = []
codeforces_durations = []

for record in data["results"]:
    if "duration_seconds" in record:
        if record["task_id"].startswith("bigobench_"):
            bigobench_durations.append(record["duration_seconds"])
        else:
            codeforces_durations.append(record["duration_seconds"])

# Combine for bin calculation
all_durations = bigobench_durations + codeforces_durations
bins = np.linspace(min(all_durations), max(all_durations), 15)

# Plot histogram with shared bins
plt.figure(figsize=(10,6))

plt.hist(bigobench_durations, bins=bins, alpha=0.6, label="BigOBench",
         color="royalblue", edgecolor="black", linewidth=1.2)
plt.hist(codeforces_durations, bins=bins, alpha=0.6, label="Codeforces",
         color="salmon", edgecolor="black", linewidth=1.2)

plt.title("Histogram of Duration (seconds) by Task Category")
plt.xlabel("Duration (seconds)")
plt.ylabel("Frequency")
plt.legend()
plt.grid(axis="y", linestyle="--", alpha=0.6)

# Force y-axis ticks to multiples of 4
plt.gca().yaxis.set_major_locator(MultipleLocator(4))

# Save to file
plt.savefig("fig_1.png", dpi=300, bbox_inches="tight")
plt.close()
