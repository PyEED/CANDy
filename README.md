# Carbohydrate Active eNzyme Domain analYsis tool (CANDy) - automated analysis of domain architectures in carbohydrate-active enzymes

CANDy is a fast, FAIR and seamless protein domain analysis tool for any [CAZy](http://www.cazy.org/) family.

**This branch is a work-in-progress rewrite of CANDy as an installable Python package** (CLI + Python API), replacing the original Google Colab / Jupyter Notebook implementation. The previous notebook (`CANDy v2.0.ipynb`) is still in this repository for reference, and the original is on [Google Colab](https://colab.research.google.com/drive/1ipRAwMFMDRGUinPDk2bwu1cg8fE2WY8Q?usp=sharing).

## Installation

CANDy depends on a handful of external bioinformatics tools (CD-HIT or MMseqs2 for clustering, MAFFT for alignment, FastTree for phylogenetics) that aren't distributed via PyPI. The supported install path is a conda environment that provides them, with CANDy itself installed via pip into that environment:

```bash
conda env create -f environment.yml
conda activate candy
```

This installs the external tools via bioconda and CANDy itself (editable) via pip. If you already have those tools on your PATH through some other means, you can also just `pip install -e .` directly.

To also enable automated Gemini-based domain-name curation:

```bash
pip install -e ".[gemini]"
```

## Usage

### Command line

```bash
# Query a CAZy family directly
candy run --jobname my_gh5_run --family GH5 --email you@example.com --tree

# Analyse your own FASTA file instead
candy run --jobname my_custom_run --fasta my_sequences.fasta --tree
```

Run `candy run --help` for the full list of options (taxonomy subset, clustering software/cutoff, BLAST identity threshold, max domain length, domain-overlap threshold, curation backend, ...).

### Python API

```python
from candy.config import CAZyFamilyInput, PipelineConfig, Taxonomy
from candy.pipeline import run_pipeline

config = PipelineConfig(
    input=CAZyFamilyInput(enzyme_class="GH", family_number=5, email="you@example.com", taxonomy=Taxonomy.ALL),
    jobname="my_gh5_run",
    output_dir="results",
    build_tree=True,
)
result = run_pipeline(config)
print(result.database_path, result.tree_path)
```

## Output

Results are written to `{output_dir}/{jobname}/`:

- FASTA files for each processing stage
- A SQLite database (`{jobname}_db.db`) containing the domain annotations -- open it with [DB Browser for SQLite](https://sqlitebrowser.org/)
- A protein domain co-occurrence network (`{jobname}_domain_cooccurence_network.graphml`) -- open it in [Cytoscape](https://cytoscape.org/) (yFiles Organic Layout recommended)
- If `--tree`/`build_tree=True`: a MAFFT alignment, a FastTree phylogenetic tree (Newick), and [iTOL](https://itol.embl.de/) annotation files for the domain architecture and (for CAZy family queries) characterized-enzyme activity

## Acknowledgements

CANDy communicates with and/or references the following separate libraries, packages and tools:

- [Biopython](https://biopython.org/)
- [pandas](https://pandas.pydata.org/)
- [tqdm](https://github.com/tqdm/tqdm)
- [sqlitebrowser](https://sqlitebrowser.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [requests](https://requests.readthedocs.io/en/latest/)
- [CD-HIT](https://academic.oup.com/bioinformatics/article/22/13/1658/194225?login=true)
- [MMseqs2](https://www.nature.com/articles/nbt.3988)
- [MAFFT](https://academic.oup.com/nar/article/30/14/3059/2904316?login=true)
- [FastTree](http://www.microbesonline.org/fasttree/)
- [NetworkX](https://networkx.org/)
- [Matplotlib](https://matplotlib.org/)

## Citation

If you find CANDy useful, please cite it as:

Windels A, Franceus J, Pleiss J, Desmet T. CANDy: Automated analysis of domain architectures in carbohydrate-active enzymes. PLoS One. 2024 Jul 11;19(7):e0306410. doi: 10.1371/journal.pone.0306410. PMID: 38990885; PMCID: PMC11238990.

## Legal terms

### License and Disclaimer

CANDy is licensed under [MIT](https://github.com/PyEED/CANDy/blob/main/SECURITY.md#mit-license).

CANDy and other information provided is for theoretical utilisation only, caution should be exercised in its use. It is provided 'as-is' without any warranty of any kind, whether expressed or implied. Information is not intended to be a substitute for professional medical advice, diagnosis, or treatment, and does not constitute medical or other professional advice.

### Third-party software

Use of the third-party software, libraries or code referred to in the [Acknowledgements section](https://github.com/PyEED/CANDy#acknowledgements) in the CANDy README may be governed by separate terms and conditions or license provisions. Your use of the third-party software, libraries or code is subject to any such terms and you should check that you can comply with any applicable restrictions or terms and conditions before use.

### Databases

The following databases are used by CANDy, and are available with reference to the following:
- UniProt: (unmodified), by The UniProt Consortium, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/).
- NCBI: (unmodified), by the National Library of Medicine, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/).
- CAZy: (unmodified), by http://www.cazy.org/ and Elodie Drula, Marie-Line Garron, Suzan Dogan, Vincent Lombard, Bernard Henrissat, Nicolas Terrapon, The carbohydrate-active enzyme database: functions and literature, Nucleic Acids Research, Volume 50, Issue D1, 7 January 2022, Pages D571–D577, https://doi.org/10.1093/nar/gkab1045, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/).
- InterPro: (unmodified), by EMBL-EBI, available under a [Creative Commons Attribution-NoDerivatives 4.0 International License](http://creativecommons.org/licenses/by-nd/4.0/).
