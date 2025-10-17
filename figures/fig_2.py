import json
import matplotlib.pyplot as plt

with open('research_results_20250824_192037.json', 'r') as file:
    data = json.load(file)

tasks = ["bigobench_binary_search", "cf_1285e_delete_a_segment", "cf_1286c2_madness_hard"]

dat = []

for entry in data["results"]:
    task_name = entry.get("task_id")
    if task_name not in tasks or entry["status"] != "success":
        continue
    rpt = entry["profile_report"]
    dat.append([])
    for x, y in zip(rpt["input_sizes"], rpt["runtime_ms"]):
        if x != 0:
            dat[-1].append([x, y])
    tasks.remove(task_name)

plt.figure(figsize=(10, 6))
for cur, lbl in zip(dat, ["bigobench_binary_search", "cf_1285e_delete_a_segment", "cf_1286c2_madness_hard"]):
    plt.scatter([x[0] for x in cur], [x[1] for x in cur], label=lbl)

plt.xlabel("Input Size")
plt.ylabel("Runtime (ms)")
plt.title("Input Size vs. Runtime for Various Tasks")
plt.legend()
plt.grid(True)

plt.savefig("fig_2.svg", bbox_inches="tight")
