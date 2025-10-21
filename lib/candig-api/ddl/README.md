## Clinical Database Setup

This script creates the clinical database from scratch.
It will:

1. Build the database structure: Use the [OMOP DDL](https://github.com/OHDSI/CommonDataModel) version 5.4 files to create the database schema.

2. Load the vocabulary (VOCAB): Import the CSV files that are compatible with Athena datasets.

### Downloading Vocabulary Data

- Visit [Athena OHDSI](https://athena.ohdsi.org/) and select the vocabulary datasets you want to download.
- Run the CPT-4 script to update CONCEPT.csv.
- Copy the CSV files into the vocab_data/ folder.

### Run the setup script

- Replace candig-api_setup with omop_db_setup
- Rebuild the stack as normal
