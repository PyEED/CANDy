# Carbohydrate Active eNzyme Domain analYsis tool (CANDy) - automated analysis of domain architectures in carbohydrate-active enzymes

CANDy is a fast, FAIR and seamless protein domain analysis tool for any [CAZy](http://www.cazy.org/) family.

CANDy is available as an installable Python package (CLI + Python API), replacing the original Google Colab / Jupyter Notebook implementation. The previous notebook (`archive/CANDy v2.0.ipynb`) is kept in this repository for reference, and the original is on [Google Colab](https://colab.research.google.com/drive/1ipRAwMFMDRGUinPDk2bwu1cg8fE2WY8Q?usp=sharing).

## Installation

```bash
pip install candy-cazyme
```

That's it for most users -- CANDy's default toolchain is fully bundled:

- **Clustering**: [MMseqs2](https://github.com/soedinglab/MMseqs2) -- auto-downloaded and cached on first use (no conda needed). On Linux/macOS this just works. On **Windows**, MMseqs2's clustering workflows internally need a POSIX shell; the official Windows build handles this itself by installing a small helper (`busybox`) the first time it runs, which may ask for administrator permission **once** -- never again after that. (This mirrors upstream: MMseqs2's own docs list WSL as the recommended Windows path and this static build as the fallback for anyone who can't use WSL.)
- **MSA**: [FAMSA](https://github.com/refresh-bio/FAMSA) via [`pyfamsa`](https://github.com/althonos/pyfamsa) -- a real pip dependency, runs in-process, no download needed.
- **Phylogenetics**: [VeryFastTree](https://github.com/citiususc/veryfasttree) via [`veryfasttree`](https://github.com/citiususc/veryfasttree-python) -- also a real pip dependency, no download needed.

If you'd rather use the original CD-HIT/MAFFT/FastTree tools instead (e.g. to reproduce results bit-for-bit against the published notebook), a conda environment with those is still provided:

```bash
conda env create -f environment.yml   # only needed for CD-HIT as a clustering alternative to MMseqs2
conda activate candy
```
and pass `--clustering-software cd-hit` / build a `PipelineConfig` with `alignment_tool="mafft"`, `tree_tool="fasttree"`.

To also enable automated Gemini-based domain-name curation:

```bash
pip install -e ".[gemini]"
```

If you'd rather not have CANDy download anything automatically (e.g. air-gapped environments), set `CANDY_NO_AUTO_DOWNLOAD=1` -- clustering will then require `mmseqs`/`cd-hit` already on PATH.

## Usage

### Command line

```bash
# Query a CAZy family directly -- TARGET is auto-detected as a family code or a file path
candy GH173 --email you@example.com --tree

# Restrict to a taxonomic subset, and use a stricter clustering cutoff
candy GH173 --email you@example.com --taxonomy Bacteria --cluster-identity 90

# Reprioritize which InterPro database wins when two disagree on a domain boundary
# (only the databases you name move; everything else keeps its default order)
candy GH173 --email you@example.com --db-preference PFAM,SMART

# Analyse your own FASTA file instead
candy my_sequences.fasta --tree
```

`--email` falls back to the `CANDY_EMAIL` environment variable, then an interactive prompt, so `export CANDY_EMAIL=you@example.com` once and just run `candy GH173` from then on. Run `candy --help` for the full list of options.

### Domain-name curation

Partway through a run, CANDy needs to decide which raw InterPro domain names (often several near-duplicates from different member databases) should be grouped under one umbrella name. By default (`--curation-backend manual`) it asks you interactively: it prints a numbered list of the domain names still to curate, then prompts twice --

1. `Domain name:` -- type the umbrella name you want to use (e.g. `Catalytic domain`)
2. `Includes:` -- type the comma-separated numbers of the domains that belong under it (e.g. `0,2`)

It repeats this until every domain is grouped; type `STOP` at the `Domain name:` prompt at any point to leave all remaining domains as their own individual groups.

To skip this entirely, use Gemini to curate automatically instead:

1. Install the extra: `pip install -e ".[gemini]"`
2. Get a free API key at [aistudio.google.com/app/api-keys](https://aistudio.google.com/app/api-keys)
3. Run with `--curation-backend gemini --curation-api-key YOUR_KEY`, or set it once via `$env:GOOGLE_API_KEY="YOUR_KEY"` (PowerShell) / `export GOOGLE_API_KEY=YOUR_KEY` (bash) and just pass `--curation-backend gemini`

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
- If `--tree`/`build_tree=True`: a FAMSA alignment, a VeryFastTree phylogenetic tree (Newick), and [iTOL](https://itol.embl.de/) annotation files for the domain architecture and (for CAZy family queries) characterized-enzyme activity

## Acknowledgements

CANDy communicates with and/or references the following separate libraries, packages and tools:

- [Biopython](https://biopython.org/)
- [pandas](https://pandas.pydata.org/)
- [tqdm](https://github.com/tqdm/tqdm)
- [sqlitebrowser](https://sqlitebrowser.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [requests](https://requests.readthedocs.io/en/latest/)
- [MMseqs2](https://www.nature.com/articles/nbt.3988) / [CD-HIT](https://academic.oup.com/bioinformatics/article/22/13/1658/194225?login=true) (clustering)
- [FAMSA](https://academic.oup.com/nar/article/44/16/e121/2468101) via [pyfamsa](https://github.com/althonos/pyfamsa) / [MAFFT](https://academic.oup.com/nar/article/30/14/3059/2904316?login=true) (alignment)
- [VeryFastTree](https://academic.oup.com/bioinformatics/article/36/17/4658/5850991) via [veryfasttree](https://github.com/citiususc/veryfasttree-python) / [FastTree](http://www.microbesonline.org/fasttree/) (phylogenetics)
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
