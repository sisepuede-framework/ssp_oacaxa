# SSP_Oaxaca

Este repositorio contiene la calibración del modelo **SISEPUEDE** para el estado de
**Oaxaca, México**, partiendo de la base de datos nacional mexicana.

## Calibración

La corrida baseline reproduce en **2013** el inventario de la **Tabla 7 del PECC Oaxaca
2016–2022** (Inventario estatal de GEI): **17,055 kt CO2e modelados vs 17,968 kt
observados, −5 %**, con las cuatro categorías IPCC dentro del ±15 %.

```bash
bash calibration/run_all.sh --run
```

Reconstruye los inputs de Oaxaca desde la base nacional intacta, corre el modelo e
imprime la tabla de validación. Ver `calibration/FINAL_REPORT.md` para el resultado
completo, `calibration/DECISIONS.md` para las decisiones estructurales y
`calibration/02_downscaling_strategy.md` para la metodología.

**Entorno:** `ssp_mex_env` (NO el nombrado en `environment.yml`, que está incompleto).


## Instructions: Setting Up the SISEPUEDE Environment

### 1. **Go to the `environment.yml` file**

Obtain the provided `environment.yml` file for SISEPUEDE.

### 2. **Set a Custom Environment Name**

Open the `environment.yml` file in your preferred text editor (such as VS Code, Atom, nano, or even Notepad).
At the very top, you'll see a line like:

```yaml
name: sisepuede
```

**Change `sisepuede` to your preferred environment name, usually related to the region you are working with** (e.g., `ssp-egypt`, `ssp-usa`, or whatever you'd like).

For example:

```yaml
name: ssp-egypt
```

### 3. **Create the Environment from the `.yml` File**

In your terminal, navigate to the directory containing your `environment.yml` file, then run:

```bash
conda env create -f environment.yml
```

This will create a new Conda environment with the name you set in the file.

### 4. **Activate the Environment**

After installation, activate your new environment with:

```bash
conda activate <your_env_name>
```

*(Replace `<your_env_name>` with the name you specified in the `.yml` file, e.g., `ssp-egypt`)*


### 5. **Done!**

Your environment is now ready to use, with all dependencies (including those installed via pip) preconfigured.


#### **Tips:**

* If you update the `environment.yml` file later, you can update your environment with:

  ```bash
  conda env update -f environment.yml --prune
  ```
* You can list all your environments with:

  ```bash
  conda env list
  ```
## Project Structure

The most relevant files are inside the `ssp_modeling` directory:

- `config_files/` – YAML configuration files used by the notebooks.
- `input_data/` – Raw CSVs for each scenario.
- `notebooks/` – Jupyter notebooks that manage the modeling runs.
- `ssp_run/` – Output folders created after executing a scenario.
- `scenario_mapping/` – Spreadsheets with the mapping between SSP transformations and region-specific measures. This is where the scenarios and transformation intensities are defined.
- `transformations/` – CSVs and YAML files describing the transformations applied by the model.
- `output_postprocessing/` – R scripts used to rescale model results and
    generate processed outputs.

## Steps to run the model and load data to Tableau for analysis

All files and folders referenced here are inside the `ssp_modeling` directory.

1. **Run the model in the notebook**

   * Edit or create a configuration file in `config_files/`.
   * Set up the transformations spreadsheet for custom Strategies and save it in `scenario_mapping/`.
   * Open the manager notebook inside `notebooks/` and run the cells to execute the model.

2. **Post-process results**
    * If you require emission targets, generate the targets file by following the instructions in the [ssp_emission_targets repository](https://github.com/sisepuede-framework/ssp_emission_targets).
    * Run the `postprocessing_250820.r` script, editing it to point to the correct data.
    * The script will generate three files; two of them are used in Tableau.

3. **Load data into Tableau**

   * In the `tableau` directory, locate the Tableau dashboard file and the `data` folder.
   * Copy the postprocessing output files into the `data` folder.
   * Load the files beginning with `decomposed_emissions_` and `drivers_` into Tableau.
