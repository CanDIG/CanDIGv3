#!/bin/bash
set -e


# --- OMOP SQL Files ---
DDL_FILE="ddl/ddl.sql"
PK_FILE="ddl/primary_keys.sql"
FK_FILE="ddl/constraints.sql"
INDICES_FILE="ddl/indices.sql"
CLEANUP_FILE="ddl/cleanup_constraints.sql"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
PASSWORD_FILE="${PROJECT_ROOT}/tmp/postgres/db-secret"


# --- Directory for Vocabulary CSV files ---
VOCAB_DATA_DIR="${SCRIPT_DIR}/vocab_data"

echo
echo "--- Starting OMOP Database Setup ---"

echo "Step 1: Get database password"
if [ ! -f "${PASSWORD_FILE}" ]; then
  echo "Error: Password file not found at '${PASSWORD_FILE}'"
  exit 1
fi

export PGPASSWORD=$(cat "${PASSWORD_FILE}")
echo "---"


# Wait for db container to be ready
echo "Waiting for db to be ready..."
# Find db container by name
DB_CONTAINER_NAME=$(docker ps --filter "name=${DB_HOST}" --format "{{.Names}}")
if [ -z "${DB_CONTAINER_NAME}" ]; then
  echo -e "ERROR: No running container found with a name matching '${DB_HOST}'"
  exit 1
fi

until docker exec "${DB_CONTAINER_NAME}" pg_isready -h localhost -p "${DB_PORT}" -U "${DEFAULT_ADMIN_USER}"; do
  echo "Waiting for the database to be ready..."
  sleep 1
done
echo "PostgreSQL is ready."
echo "---"

# Check if the database already exists. If so, drop and recreate it
echo "Step 2: Checking if database '${DB_NAME}' already exists..."

if docker exec "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
    echo "Database '${DB_NAME}' already exists. Dropping and recreating..."
    docker exec "${DB_CONTAINER_NAME}" dropdb -U "${DEFAULT_ADMIN_USER}" "${DB_NAME}"
    echo "Database '${DB_NAME}' dropped successfully."
fi

echo "Creating database '${DB_NAME}'..."
docker exec "${DB_CONTAINER_NAME}" createdb -U "${DEFAULT_ADMIN_USER}" "${DB_NAME}"
echo "Database '${DB_NAME}' created successfully."

# Create the schema
echo "---"
echo "Step 3: Creating schema '${CDM_SCHEMA}'..."
docker exec "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" -c "CREATE SCHEMA ${CDM_SCHEMA};"
echo "Schema '${CDM_SCHEMA}' created successfully."
echo "---"

TEMP_DIR=$(mktemp -d)

run_sql_file() {
  local description=$1
  local input_file=$2
  local processed_file="${TEMP_DIR}/$(basename "$input_file")"
  local full_input_path="${SCRIPT_DIR}/${input_file}"

  echo "Starting: ${description}..."

  if [ ! -f "$full_input_path" ]; then
    echo "Error: Source file '${full_input_path}' not found."
    rm -rf "${TEMP_DIR}"
    exit 1
  fi

  sed "s/@cdmDatabaseSchema\./${CDM_SCHEMA}\./g" "$full_input_path" > "$processed_file"

  cat "$processed_file" | docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" --quiet
}

# Function to load data from CSV files into the database
load_vocab_data() {
  local vocab_dir=$1
  echo "--- Starting Vocabulary CSV Data Load ---"

  if [ ! -d "$vocab_dir" ]; then
    echo "Error: Vocabulary directory '${vocab_dir}' not found."
    return 1
  fi

  # List of vocabulary tables to load, in order - use an array instead
  local tables=("VOCABULARY" "RELATIONSHIP" "DOMAIN" "CONCEPT" "CONCEPT_RELATIONSHIP" "CONCEPT_ANCESTOR" "CONCEPT_SYNONYM" "CONCEPT_CLASS" "DRUG_STRENGTH")

  for table in "${tables[@]}"; do
    local csv_file="${vocab_dir}/${table}.csv"

    if [ ! -f "$csv_file" ]; then
      echo "Warning: CSV file for table '${table}' not found at '${csv_file}'. Skipping."
      continue
    fi

    echo "Loading data for table: ${table}"
    if ! cat "$csv_file" | sed 's/"/""/g' | docker exec -i "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" \
        -c "\COPY ${CDM_SCHEMA}.${table} FROM STDIN (DELIMITER E'\t', FORMAT CSV, HEADER, NULL '', QUOTE '\"', ESCAPE '\"')"; then
        echo "Error loading data for table: ${table}. Exit code: $?"
        echo "Checking if table exists..."
        docker exec "${DB_CONTAINER_NAME}" psql -U "${DEFAULT_ADMIN_USER}" -d "${DB_NAME}" \
            -c "\d ${CDM_SCHEMA}.${table}"
        exit 1
    fi

    if [ $? -eq 0 ]; then
      echo "Successfully loaded: ${table}"
    else
      echo "Error loading data for table: ${table}. Please check the CSV format and table structure."
    fi
  done

  echo "--- Vocabulary CSV Data Load Complete ---"
}


# Run SQL files
run_sql_file "Creating Tables (DDL)" "$DDL_FILE"
run_sql_file "Adding Primary Keys" "$PK_FILE"

# Import VOCAB, make sure to place csv files in vocab_data folder
load_vocab_data "$VOCAB_DATA_DIR"

# Uncomment this script if the csv needs clean up
# run_sql_file "Cleaning up orphan rows" "$CLEANUP_FILE"

run_sql_file "Adding Foreign Key Constraints" "$FK_FILE"
run_sql_file "Creating Indices" "$INDICES_FILE"



echo "--- OMOP Setup Complete! ---"
echo "Database '${DB_NAME}' is ready on container '${DB_CONTAINER_NAME}'."

unset PGPASSWORD
rm -rf "${TEMP_DIR}"