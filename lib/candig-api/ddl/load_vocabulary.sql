--Load vocabularies
\copy omop.concept FROM 'tmp/omopdata/concept.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_ancestor FROM 'tmp/omopdata/concept_ancestor.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_class FROM 'tmp/omopdata/concept_class.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_relationship FROM 'tmp/omopdata/concept_relationship.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_synonym FROM 'tmp/omopdata/concept_synonym.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.domain FROM 'tmp/omopdata/domain.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.relationship FROM 'tmp/omopdata/relationship.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.vocabulary FROM 'tmp/omopdata/vocabulary.csv' WITH (FORMAT CSV, HEADER true);