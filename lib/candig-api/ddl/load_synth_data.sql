--Load vocabularies
\copy omop.concept FROM 'tmp/omopdata/concept.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_ancestor FROM 'tmp/omopdata/concept_ancestor.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_class FROM 'tmp/omopdata/concept_class.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_relationship FROM 'tmp/omopdata/concept_relationship.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.concept_synonym FROM 'tmp/omopdata/concept_synonym.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.domain FROM 'tmp/omopdata/domain.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.relationship FROM 'tmp/omopdata/relationship.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.vocabulary FROM 'tmp/omopdata/vocabulary.csv' WITH (FORMAT CSV, HEADER true);

--Load synth data
\copy omop.care_site FROM 'tmp/omopdata/care_site.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.cdm_source FROM 'tmp/omopdata/cdm_source.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.condition_occurrence FROM 'tmp/omopdata/condition_occurrence.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.cost FROM 'tmp/omopdata/person.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.death FROM 'tmp/omopdata/death.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.device_exposure FROM 'tmp/omopdata/device_exposure.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.dose_era FROM 'tmp/omopdata/dose_era.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.drug_era FROM 'tmp/omopdata/drug_era.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.drug_exposure FROM 'tmp/omopdata/drug_exposure.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.episode FROM 'tmp/omopdata/episode.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.episode_event FROM 'tmp/omopdata/episode_event.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.location FROM 'tmp/omopdata/location.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.measurement FROM 'tmp/omopdata/measurement.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.note FROM 'tmp/omopdata/note.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.observation FROM 'tmp/omopdata/observation.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.observation_period FROM 'tmp/omopdata/observation_period.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.payer_plan_period FROM 'tmp/omopdata/payer_plan_period.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.person FROM 'tmp/omopdata/person.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.provider FROM 'tmp/omopdata/provider.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.specimen FROM 'tmp/omopdata/specimen.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.visit_detail FROM 'tmp/omopdata/visit_detail.csv' WITH (FORMAT CSV, HEADER true);
\copy omop.visit_occurrence FROM 'tmp/omopdata/visit_occurrence.csv' WITH (FORMAT CSV, HEADER true);
