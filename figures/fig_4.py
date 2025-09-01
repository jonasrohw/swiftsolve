import json
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

with open('research_results_20250824_192037.json', 'r') as file:
    data = json.load(file)

dat = [16, 20, 21]

plt.xlabel("Replan ID")
plt.ylabel("Count")
plt.title("Success Counts for Each Replan")

plt.gca().yaxis.set_major_locator(MultipleLocator(4))

plt.bar(["Replan 0", "Replan 1", "Replan 2"], dat)

plt.savefig('fig_4.png', bbox_inches='tight')
