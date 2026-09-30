# LLM-dependent harness (LDH) extraction

Extract source regions for Augment from Python or TypeScript projects. Run commands from the repository root.

## Inputs

Provide a checkout and [source_files.json](../../resources/inputs/README.md#source_filesjson) listing source files and local dependencies needed for analysis, including unexecuted files. Python needs an interpreter supporting the source syntax. TypeScript needs Node.js, Python 3, and a TypeScript installation.

## Run

For either language, [register the project](../../SETUP.md#new-projects), then run:

```bash
python3 run.py llm-dependent --project my-project \
  --project-root /path/to/checkout \
  --source-base /path/to/inputs/source_files.json \
  --out /path/to/inputs/regions.json
```

Use `--typescript-root PATH` to select a directory containing the TypeScript installation; the default is the checkout.

## Outputs

The main output defaults to `outputs/<project>/extraction/regions.json`. `--out` accepts a `.json` filename or an output directory; a directory produces `regions.json` inside it. Reference the main output as `ldh.regions_json` in Augment's [base_input.json](../../resources/inputs/README.md#base_inputjson); coverage must come from the same checkout revision.
