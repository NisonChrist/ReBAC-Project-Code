import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

nl_root = Path("policy_generation/output/litroacp/")
nl_paths = [
    nl_root / "acre_acp.csv",
    nl_root / "collected_acp.csv",
    nl_root / "cyber_acp.csv",
    nl_root / "ibm_acp.csv",
    nl_root / "t2p_acp.csv",
]

xacml_root = Path("policy_generation/output/xacml/xacBench")
xacml_paths = [
    xacml_root / "xacml2_1.csv",
    xacml_root / "xacml2_2.csv",
    xacml_root / "xacml2_3.csv",
    xacml_root / "xacml3_1.csv",
    xacml_root / "xacml3_2.csv",
    xacml_root / "xacml3_3.csv",
]

for path in xacml_paths:
    df = pd.read_csv(path)
    print(path.stem, df.shape)

data_completeness = []
dataset_names = []
colors = []

# Process NL datasets
for path in nl_paths:
    df = pd.read_csv(path)
    # Calculate percentage of rows with no empty fields
    complete_rows = df.dropna().shape[0]
    total_rows = df.shape[0]
    percentage = (complete_rows / total_rows * 100) if total_rows > 0 else 0
    data_completeness.append(percentage)
    dataset_names.append(path.stem)
    colors.append("#a9c4eb")  # Light blue for NL datasets

# Process XACML datasets
for path in xacml_paths:
    df = pd.read_csv(path)
    complete_rows = df.dropna().shape[0]
    total_rows = df.shape[0]
    percentage = (complete_rows / total_rows * 100) if total_rows > 0 else 0
    data_completeness.append(percentage)
    dataset_names.append(path.stem)
    colors.append("#ffce9f")  # Light orange for XACML datasets

# Plotting (vertical bars) — thinner bars, tighter x spacing
fig, ax = plt.subplots(figsize=(4, 3))
x_pos = np.arange(len(dataset_names))
x_pos = x_pos * 0.8  # Reduce spacing between bars
# Make bars thinner via width and reduce category spacing visually
bars = ax.bar(x_pos, data_completeness, align="center", color=colors, width=0.5)

# Tighter x-axis: minimal margins and compact tick labels
ax.margins(x=0.03)
ax.set_xticks(x_pos)
ax.set_xticklabels(dataset_names, rotation=90,  fontsize=6)

ax.set_ylabel("Percentage of Complete Rows (%)", fontsize=6)
ax.set_title("Percentage of Rows with No Empty Fields per Dataset", fontsize=9)
ax.tick_params(axis='y', labelsize=6)
ax.set_ylim(0, 115)  # Extend a bit for labels

# Add percentage labels above bars
for i, v in enumerate(data_completeness):
    ax.text(x_pos[i], v + 1, f"{v:.1f}%", ha="center", va="bottom", fontsize=5)

# Add legend
legend_elements = [
    Patch(facecolor='#a9c4eb', label='Natural Language Statements'),
    Patch(facecolor='#ffce9f', label='XACML')
]
ax.legend(handles=legend_elements, fontsize=5, loc='upper center', ncol=2, shadow=False,edgecolor='none')

fig.tight_layout()
# fig.subplots_adjust(bottom=0.18)
fig.savefig("evaluation/policy_gen_result.png", dpi=600)
plt.show()