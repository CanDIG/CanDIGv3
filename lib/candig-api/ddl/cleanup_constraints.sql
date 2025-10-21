-- ddl/combined_cleanup.sql
--
-- This single, optimized script prepares the database for foreign key constraints.
-- It performs three main steps:
--  1. Creates temporary indexes to make the DELETE operations fast.
--  2. Deletes orphan records that would violate foreign key constraints.
--  3. Drops the temporary indexes to clean up.
--

\echo '--- Starting Data Cleanup ---'
\timing on

-- Step 1: Create temporary indexes to accelerate DELETEs.
\echo
\echo '[INFO] Step 1 of 3: Creating temporary indexes...'

CREATE INDEX idx_temp_concept_relationship_id_1 ON omop.concept_relationship (concept_id_1);
CREATE INDEX idx_temp_concept_relationship_id_2 ON omop.concept_relationship (concept_id_2);
CREATE INDEX idx_temp_concept_synonym_id ON omop.concept_synonym (concept_id);
CREATE INDEX idx_temp_concept_ancestor_anc_id ON omop.concept_ancestor (ancestor_concept_id);
CREATE INDEX idx_temp_concept_ancestor_desc_id ON omop.concept_ancestor (descendant_concept_id);

-- Step 2: Delete orphan records using an efficient pattern.
\echo
\echo '[INFO] Step 2 of 3: Deleting orphan rows...'

\echo ' -> Deleting from concept_relationship...'
DELETE FROM omop.concept_relationship
WHERE NOT EXISTS (SELECT 1 FROM omop.concept WHERE concept_id = concept_id_1)
   OR NOT EXISTS (SELECT 1 FROM omop.concept WHERE concept_id = concept_id_2);

\echo ' -> Deleting from concept_synonym...'
DELETE FROM omop.concept_synonym cs
WHERE NOT EXISTS (SELECT 1 FROM omop.concept c WHERE c.concept_id = cs.concept_id);

\echo ' -> Deleting from concept_ancestor...'
DELETE FROM omop.concept_ancestor
WHERE NOT EXISTS (SELECT 1 FROM omop.concept WHERE concept_id = ancestor_concept_id)
   OR NOT EXISTS (SELECT 1 FROM omop.concept WHERE concept_id = descendant_concept_id);


-- Step 3: Drop the temporary indexes. They are no longer needed.
\echo
\echo '[INFO] Step 3 of 3: Dropping temporary indexes...'

DROP INDEX omop.idx_temp_concept_relationship_id_1;
DROP INDEX omop.idx_temp_concept_relationship_id_2;
DROP INDEX omop.idx_temp_concept_synonym_id;
DROP INDEX omop.idx_temp_concept_ancestor_anc_id;
DROP INDEX omop.idx_temp_concept_ancestor_desc_id;


\timing off
\echo
\echo '--- Data Cleanup Complete ---'