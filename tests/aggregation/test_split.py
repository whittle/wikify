from hypothesis import given
from hypothesis import strategies as st

from wikify.aggregation.split import (
    aggregate_fact,
    all_entity_data_for_session,
    extract_facts_about_entity,
    extract_references_to_entity,
    reference_fact,
    session_entity_data,
)
from wikify.models.entity import AggregatedFact, EntityData, Reference
from wikify.models.extraction import ExtractedEntity, ExtractionResult
from wikify.models.fact import Fact


class TestAggregateFact:
    @given(st.builds(Fact), st.integers())
    def test_text_identity(self, fact, session_num):
        result: AggregatedFact = aggregate_fact(fact, session_num)

        assert result.text == fact.text

    @given(st.builds(Fact), st.integers())
    def test_category_identity(self, fact, session_num):
        result: AggregatedFact = aggregate_fact(fact, session_num)

        assert result.category == fact.category

    @given(st.builds(Fact), st.integers())
    def test_confidence_identity(self, fact, session_num):
        result: AggregatedFact = aggregate_fact(fact, session_num)

        assert result.confidence == fact.confidence

    @given(st.builds(Fact, object_entities=st.lists(st.text())), st.integers())
    def test_object_entities_identity(self, fact, session_num):
        result: AggregatedFact = aggregate_fact(fact, session_num)

        assert result.object_entities == fact.object_entities

    @given(st.builds(Fact), st.integers())
    def test_source_session_identity(self, fact, session_num):
        result: AggregatedFact = aggregate_fact(fact, session_num)

        assert result.source_session == session_num


class TestReferenceFact:
    @given(st.builds(Fact), st.integers())
    def test_source_entity_identity(self, fact, session_num):
        result: Reference = reference_fact(fact, session_num)

        assert result.source_entity == fact.subject_entity

    @given(st.builds(Fact), st.integers())
    def test_fact_text_identity(self, fact, session_num):
        result: Reference = reference_fact(fact, session_num)

        assert result.fact_text == fact.text

    @given(st.builds(Fact), st.integers())
    def test_source_session_identity(self, fact, session_num):
        result: Reference = reference_fact(fact, session_num)

        assert result.source_session == session_num


class TestExtractFactsAboutEntity:
    @given(st.data())
    def test_count_of_facts_extracted(self, data):
        entities = data.draw(
            st.lists(
                st.builds(ExtractedEntity), min_size=1, unique_by=lambda a: a.entity_id
            )
        )
        entity = entities[0]
        relevant_facts = data.draw(
            st.lists(st.builds(Fact, subject_entity=st.just(entity.entity_id)))
        )
        irrelevant_facts = data.draw(
            st.lists(
                st.builds(Fact).filter(lambda a: a.subject_entity != entity.entity_id)
            )
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.permutations(entities),
                facts=st.permutations(relevant_facts + irrelevant_facts),
            )
        )

        result: list[AggregatedFact] = extract_facts_about_entity(
            extraction, entity.entity_id
        )

        assert len(result) == len(relevant_facts)

    @given(st.data())
    def test_aggregation_of_facts_extracted(self, data):
        entities = data.draw(
            st.lists(
                st.builds(ExtractedEntity), min_size=1, unique_by=lambda a: a.entity_id
            )
        )
        entity = entities[0]
        relevant_facts = data.draw(
            st.lists(
                st.builds(Fact, subject_entity=st.just(entity.entity_id)),
                unique_by=lambda a: a.text,
            )
        )
        irrelevant_facts = data.draw(
            st.lists(
                st.builds(Fact).filter(lambda a: a.subject_entity != entity.entity_id)
            )
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.permutations(entities),
                facts=st.permutations(relevant_facts + irrelevant_facts),
            )
        )

        result: list[AggregatedFact] = extract_facts_about_entity(
            extraction, entity.entity_id
        )

        for agg, orig in zip(
            sorted(result, key=lambda a: a.text),
            sorted(relevant_facts, key=lambda a: a.text),
        ):
            assert agg.text == orig.text
            assert agg.category == orig.category
            assert agg.confidence == orig.confidence
            assert agg.object_entities == orig.object_entities
            assert agg.source_session == extraction.session_number


class TestExtractReferencesToEntity:
    @given(st.data())
    def test_count_of_references_extracted(self, data):
        entities = data.draw(
            st.lists(
                st.builds(ExtractedEntity), min_size=1, unique_by=lambda a: a.entity_id
            )
        )
        entity = entities[0]
        relevant_facts = data.draw(
            st.lists(
                st.builds(
                    Fact,
                    object_entities=st.permutations(
                        [entity.entity_id] + data.draw(st.lists(st.text()))
                    ),
                )
            )
        )
        irrelevant_facts = data.draw(
            st.lists(
                st.builds(Fact).filter(
                    lambda a: entity.entity_id not in a.object_entities
                )
            )
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.permutations(entities),
                facts=st.permutations(relevant_facts + irrelevant_facts),
            )
        )

        result: list[Reference] = extract_references_to_entity(
            extraction, entity.entity_id
        )

        assert len(result) == len(relevant_facts)

    @given(st.data())
    def test_aggregation_of_references_extracted(self, data):
        entities = data.draw(
            st.lists(
                st.builds(ExtractedEntity), min_size=1, unique_by=lambda a: a.entity_id
            )
        )
        entity = entities[0]
        relevant_facts = data.draw(
            st.lists(
                st.builds(
                    Fact,
                    object_entities=st.permutations(
                        [entity.entity_id] + data.draw(st.lists(st.text()))
                    ),
                ),
                unique_by=lambda a: a.text,
            )
        )
        irrelevant_facts = data.draw(
            st.lists(
                st.builds(Fact).filter(
                    lambda a: entity.entity_id not in a.object_entities
                )
            )
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult,
                entities=st.permutations(entities),
                facts=st.permutations(relevant_facts + irrelevant_facts),
            )
        )

        result: list[Reference] = extract_references_to_entity(
            extraction, entity.entity_id
        )

        for ref, orig in zip(
            sorted(result, key=lambda a: a.fact_text),
            sorted(relevant_facts, key=lambda a: a.text),
        ):
            assert ref.source_entity == orig.subject_entity
            assert ref.fact_text == orig.text
            assert ref.source_session == extraction.session_number


class TestSessionEntityData:
    @given(st.builds(ExtractionResult), st.builds(ExtractedEntity))
    def test_entity_id_identity(self, extraction_result, entity):
        result: EntityData = session_entity_data(extraction_result, entity)

        assert result.entity_id == entity.entity_id

    @given(st.builds(ExtractionResult), st.builds(ExtractedEntity))
    def test_canonical_name_identity(self, extraction_result, entity):
        result: EntityData = session_entity_data(extraction_result, entity)

        assert result.canonical_name == entity.canonical_name

    @given(st.builds(ExtractionResult), st.builds(ExtractedEntity))
    def test_aliases_identity(self, extraction_result, entity):
        result: EntityData = session_entity_data(extraction_result, entity)

        assert result.aliases == entity.aliases

    @given(st.builds(ExtractionResult), st.builds(ExtractedEntity))
    def test_type_identity(self, extraction_result, entity):
        result: EntityData = session_entity_data(extraction_result, entity)

        assert result.type == entity.type

    @given(st.builds(ExtractionResult), st.builds(ExtractedEntity))
    def test_first_appearance_identity(self, extraction_result, entity):
        result: EntityData = session_entity_data(extraction_result, entity)

        assert result.first_appearance == entity.first_appearance

    @given(st.builds(ExtractionResult), st.builds(ExtractedEntity))
    def test_sessions_appeared_identity(self, extraction_result, entity):
        result: EntityData = session_entity_data(extraction_result, entity)

        assert result.sessions_appeared == [extraction_result.session_number]


class TestAllEntityDataForSession:
    @given(st.builds(ExtractionResult))
    def test_length(self, extraction_result):
        result: list[EntityData] = all_entity_data_for_session(extraction_result)

        assert len(result) == len(extraction_result.entities)

    @given(st.builds(ExtractionResult))
    def test_entity_ids(self, extraction_result):
        result: list[EntityData] = all_entity_data_for_session(extraction_result)

        assert {a.entity_id for a in result} == {
            a.entity_id for a in extraction_result.entities
        }

    @given(st.data())
    def test_facts_cardinality(self, data):
        """The concatenation of all facts from entities should have the same length as the input facts."""
        entities = data.draw(
            st.lists(
                st.builds(ExtractedEntity), min_size=1, unique_by=lambda a: a.entity_id
            )
        )
        facts = data.draw(
            st.lists(
                st.builds(
                    Fact,
                    subject_entity=st.sampled_from([a.entity_id for a in entities]),
                )
            )
        )
        extraction = data.draw(
            st.builds(
                ExtractionResult, entities=st.just(entities), facts=st.just(facts)
            )
        )

        result: list[EntityData] = all_entity_data_for_session(extraction)

        assert len(sum([a.facts for a in result], [])) == len(facts)
