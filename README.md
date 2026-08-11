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
- **Phylogenetics**: [VeryFastTree](https://github.com/citiususc/veryfasttree) via [`veryfasttree`](https://github.com/citiususc/veryfasttree-python) -- also a real pip dependency, no download needed. **Except on Apple Silicon Macs**: `veryfasttree` has no `macOS arm64` wheel at all (as of 4.0.4.1), so CANDy skips it there entirely and defaults `--tree-tool` to [FastTree](https://github.com/morgannprice/fasttree) instead, which auto-downloads (Linux/Windows) or auto-compiles from a single dependency-free C file (macOS) on first use, cached afterward -- no conda needed there either. See below.

### Apple Silicon (M1/M2/M3/M4) setup

There are two distinct, independent issues here -- you may hit either, both, or neither depending on your setup:

**1. `--tree` crashes with `illegal hardware instruction`, no traceback.** This means your Python itself is x86_64 running under Rosetta 2 translation instead of native `arm64` -- FAMSA ships native SIMD code, and Rosetta's emulation of some CPU instructions is a known cause of exactly this crash (it can also make other native calls, e.g. Gemini curation, unreliable). CANDy logs a warning about this at startup if detected, but **pip can't fix it for you**: by the time `pip install` runs, the interpreter architecture is already fixed.

**Step 0, always do this first:** confirm your *terminal itself* is native, not just your hardware:

```bash
arch   # must print "arm64", not "i386"
```

If it prints `i386`, your terminal app (Terminal/iTerm) is launching under Rosetta -- and anything installed from it, including tools like `uv` that are supposed to auto-detect the native architecture, will get fooled into installing x86_64 builds too. Fix this first: quit the app, Finder > select it > `Cmd+I` > uncheck "Open using Rosetta" > relaunch, then re-run `arch` to confirm.

Once `arch` says `arm64`, two ways to get a correct native Python:

**Option A -- [`uv`](https://docs.astral.sh/uv/) (recommended):** `uv` manages isolated Python installs and defaults to the native architecture -- *once its own install wasn't done under a translated shell* (see Step 0).

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # only if you don't already have uv
uv python install 3.12
uv tool install --python 3.12 "candy-cazyme[gemini]"
```

If you already ran `uv tool install` before fixing Step 0, it will have cached an x86_64 environment -- force it to redo the install natively:

```bash
uv tool uninstall candy-cazyme
uv tool install --force --python 3.12 "candy-cazyme[gemini]"
```

This gives you a `candy` command backed by its own isolated, native-arm64 Python -- no venv/PATH management needed.

**Option B -- Homebrew, manually:**

```bash
# Install (or confirm) Homebrew at the Apple Silicon prefix, /opt/homebrew
# (a pre-existing Homebrew at /usr/local is the Intel-only one):
/opt/homebrew/bin/brew --version || arch -arm64 /bin/bash -c \
  "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python from that prefix and use it explicitly:
/opt/homebrew/bin/brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install candy-cazyme
```

Either way, verify before running a real job:

```bash
python3 -c "import platform; print(platform.machine())"   # should print "arm64", not "x86_64"
```

**2. `--tree` fails to install or build `veryfasttree` (e.g. a CMake/OpenMP compiler error).** This is unrelated to Rosetta -- `veryfasttree` simply has no `macOS arm64` wheel at all, for any Python version, so `pip`/`uv` would otherwise try to build it from source there, and that build fails on stock macOS due to an upstream bug (`find_package(OpenMP)` fails, since Apple's Clang has no OpenMP support out of the box, and `veryfasttree`'s CMake fallback for that case is itself broken). **You shouldn't hit this at all as of `candy-cazyme` 3.0.4+**: on a Mac without a working native `veryfasttree` build, CANDy both skips it as an install-time dependency entirely (so nothing tries to build it) and defaults `--tree-tool` to `fasttree` instead -- which auto-downloads a precompiled binary (Linux/Windows) or, on macOS specifically (no precompiled binary is published upstream), auto-compiles one from a single dependency-free C source file using whatever C compiler is already on your machine (Xcode Command Line Tools' `clang`, already present on essentially every real Mac). No conda needed. This happens once and is cached, the same way MMseqs2 auto-downloads itself.

If that auto-compile step ever fails (e.g. genuinely no compiler on PATH), the error message tells you to run `xcode-select --install`, or you can still fall back to the bundled conda environment:

```bash
conda env create -f environment.yml
conda activate candy
```

If you'd rather force `veryfasttree` anyway (e.g. you've solved the OpenMP build issue yourself), `pip install veryfasttree` explicitly and pass `--tree-tool veryfasttree`.

If you'd rather use the original CD-HIT/MAFFT/FastTree tools instead (e.g. to reproduce results bit-for-bit against the published notebook), `environment.yml` provides CD-HIT and FastTree (`conda env create -f environment.yml && conda activate candy`, then `--clustering-software cd-hit --tree-tool fasttree`); MAFFT isn't included there (no `osx-arm64` build -- see above) and needs a separate install, e.g. `brew install mafft` on Intel Mac/Linux, then `--alignment-tool mafft`.

To also enable automated Gemini-based domain-name curation, see [Domain-name curation](#domain-name-curation) below.

If you'd rather not have CANDy download anything automatically (e.g. air-gapped environments), set `CANDY_NO_AUTO_DOWNLOAD=1` -- clustering will then require `mmseqs`/`cd-hit`, and `--tree-tool fasttree` will require `FastTree`, already on PATH.

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

# Pick a specific MSA/phylogenetics backend explicitly (see Installation for
# when you'd want to -- e.g. --tree-tool fasttree needs the conda environment)
candy GH173 --email you@example.com --tree --alignment-tool mafft --tree-tool fasttree
```

`--email` falls back to the `CANDY_EMAIL` environment variable, then an interactive prompt, so `export CANDY_EMAIL=you@example.com` once and just run `candy GH173` from then on. Run `candy --help` for the full list of options.

### Domain-name curation

Partway through a run, CANDy needs to decide which raw InterPro domain names (often several near-duplicates from different member databases) should be grouped under one umbrella name. By default (`--curation-backend manual`) it asks you interactively: it prints a numbered list of the domain names still to curate, then prompts twice --

1. `Domain name:` -- type the umbrella name you want to use (e.g. `Catalytic domain`)
2. `Includes:` -- type the comma-separated numbers of the domains that belong under it (e.g. `0,2`)

It repeats this until every domain is grouped; type `STOP` at the `Domain name:` prompt at any point to leave all remaining domains as their own individual groups.

To skip this entirely, use Gemini to curate automatically instead:

1. Install the extra: `pip install "candy-cazyme[gemini]"` (for Mac: uv tool install  "candy-cazyme[gemini]" --force --python 3.10)
2. Get a free API key at [aistudio.google.com/app/api-keys](https://aistudio.google.com/app/api-keys)
3. Run with `--curation-backend gemini --curation-api-key YOUR_KEY`, or set it once via `$env:GOOGLE_API_KEY="YOUR_KEY"` (PowerShell) / `export GOOGLE_API_KEY=YOUR_KEY` (bash) and just pass `--curation-backend gemini`

**If this step appears to hang with nothing printing** (v3.0.2+): CANDy now logs before and after the Gemini request, and bounds each attempt to a 60-second timeout, so a multi-minute wait during retries is visible and finite rather than silent. On an older version, this step had no request timeout at all and could hang indefinitely on a stalled connection with zero output -- if you hit this, `Ctrl+C`, upgrade (`pip install --upgrade candy-cazyme`), and rerun.

**If Gemini itself fails** (v3.0.3+, e.g. a `503 UNAVAILABLE` "high demand" error, a rate limit, or a model being deprecated): CANDy automatically retries once against a different model (`gemini-2.5-flash-lite` by default) before giving up on Gemini entirely. If that also fails, it automatically falls back to the interactive manual-curation prompt described above, rather than crashing and discarding the (often several-minutes-long) fetching/clustering/domain-detection work already done in that run.

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
