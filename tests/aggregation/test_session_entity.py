from hypothesis import assume, given
from hypothesis import strategies as st

from wikify.aggregation.errors import EntityDataMergeIncompatibility
from wikify.aggregation.session_entity import (
    all_entity_data_for_session,
    aggregate_fact,
    extract_facts_about_entity,
    extract_references_to_entity,
    merge_entity_data,
    reference_fact,
    session_entity_data,
)
from wikify.models.entity import AggregatedFact, EntityData, Reference
from wikify.models.extraction import ExtractedEntity, ExtractionResult
from wikify.models.fact import ConfidenceLevel, Fact


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


class TestMergeEntityData:
    def normalize_entity_data(self, data: EntityData) -> EntityData:
        return EntityData(
            entity_id=data.entity_id,
            canonical_name=data.canonical_name,
            aliases=sorted(
                list({alias for alias in data.aliases} - {data.canonical_name})
            ),
            type=data.type,
            first_appearance=data.first_appearance,
            facts=data.facts,
            referenced_by=data.referenced_by,
            sessions_appeared=sorted(data.sessions_appeared),
        )

    def test_empty_exception(self):
        """If the input list is empty, throw an exception."""
        try:
            _result: EntityData = merge_entity_data([])
        except IndexError:
            pass
        else:
            assert False

    @given(st.data())
    def test_single_identity(self, data):
        """If there’s only one element to merge, return it unchanged."""
        entity_data = self.normalize_entity_data(data.draw(st.builds(EntityData)))

        result: EntityData = merge_entity_data([entity_data])

        assert result == entity_data

    @given(st.data())
    def test_unified_entity_ids(self, data):
        """If the entities to be merged have different ids, an exception is thrown."""
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(EntityData, type=st.just(entity_type)),
                min_size=2,
                unique_by=lambda a: a.entity_id,
            )
        )

        try:
            _result: EntityData = merge_entity_data(entity_data)
        except EntityDataMergeIncompatibility:
            pass
        else:
            assume(False)

    @given(st.data())
    def test_entity_id_identity(self, data):
        """If all the input entity_ids are the same, the output entity_id also matches."""
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData, entity_id=st.just(entity_id), type=st.just(entity_type)
                ),
                min_size=2,
            )
        )

        result: EntityData = merge_entity_data(entity_data)

        assert result.entity_id == entity_id

    @given(st.data())
    def test_canonical_name_selection(self, data):
        """The canonical name of the result should be the canonical name of the final (most recent) input."""
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData, entity_id=st.just(entity_id), type=st.just(entity_type)
                ),
                min_size=2,
            )
        )

        result: EntityData = merge_entity_data(entity_data)

        assert result.canonical_name == entity_data[-1].canonical_name

    @given(st.data())
    def test_excluded_alias(self, data):
        """The canonical name of the resulting entity is excluded from its list of aliases."""
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData, entity_id=st.just(entity_id), type=st.just(entity_type)
                ),
                min_size=2,
            )
        )

        result: EntityData = merge_entity_data(entity_data)

        assert result.canonical_name not in result.aliases

    @given(st.data())
    def test_sum_aliases(self, data):
        """The aliases of the result should include all aliases of inputs, except an alias matching the canonical name of the result."""
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData, entity_id=st.just(entity_id), type=st.just(entity_type)
                ),
                min_size=2,
                unique_by=lambda a: "|".join(a.aliases),
            )
        )

        result: EntityData = merge_entity_data(entity_data)

        expected_aliases = {
            alias for entity in entity_data for alias in entity.aliases
        } - {result.canonical_name}
        assert set(result.aliases) == expected_aliases

    @given(st.data())
    def test_unified_type(self, data):
        """If the entities to be merged have different types, throw an exception."""
        entity_id = data.draw(st.text())
        entity_datas = data.draw(
            st.lists(
                st.builds(EntityData, entity_id=st.just(entity_id)),
                min_size=2,
                unique_by=lambda a: a.type,
            )
        )

        try:
            _result: EntityData = merge_entity_data(entity_datas)
        except EntityDataMergeIncompatibility:
            pass
        else:
            assert False

    @given(st.data())
    def test_first_appearance_selected(self, data):
        """Select the minimum as the first appearance."""
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        first_appearance = data.draw(st.integers(min_value=0))
        min_entity_data = data.draw(
            st.builds(
                EntityData,
                entity_id=st.just(entity_id),
                type=st.just(entity_type),
                first_appearance=st.just(first_appearance),
            )
        )
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData,
                    entity_id=st.just(entity_id),
                    type=st.just(entity_type),
                    first_appearance=st.integers(min_value=first_appearance),
                ),
                min_size=2,
            )
        )
        all_entity_data = data.draw(st.permutations([min_entity_data] + entity_data))

        result: EntityData = merge_entity_data(all_entity_data)

        assert result.first_appearance == first_appearance

    @given(st.data())
    def test_all_facts_collected(self, data):
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData, entity_id=st.just(entity_id), type=st.just(entity_type)
                ),
                min_size=2,
            )
        )

        result: EntityData = merge_entity_data(entity_data)

        def tupleize(
            fact: AggregatedFact,
        ) -> tuple[str, str, ConfidenceLevel, str, int]:
            return (
                fact.text,
                fact.category,
                fact.confidence,
                ",".join(fact.object_entities),
                fact.source_session,
            )

        assert {tupleize(fact) for fact in result.facts} == {
            tupleize(fact) for entity in entity_data for fact in entity.facts
        }

    @given(st.data())
    def test_all_references_collected(self, data):
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData, entity_id=st.just(entity_id), type=st.just(entity_type)
                ),
                min_size=2,
            )
        )

        result: EntityData = merge_entity_data(entity_data)

        def tupleize(ref: Reference) -> tuple[str, str, int]:
            return (
                ref.source_entity,
                ref.fact_text,
                ref.source_session,
            )

        assert {tupleize(ref) for ref in result.referenced_by} == {
            tupleize(ref) for entity in entity_data for ref in entity.referenced_by
        }

    @given(st.data())
    def test_all_session_appearances_collected(self, data):
        entity_id = data.draw(st.text())
        entity_type = data.draw(st.text())
        entity_data = data.draw(
            st.lists(
                st.builds(
                    EntityData, entity_id=st.just(entity_id), type=st.just(entity_type)
                ),
                min_size=2,
            )
        )

        result: EntityData = merge_entity_data(entity_data)

        assert set(result.sessions_appeared) == {
            session for entity in entity_data for session in entity.sessions_appeared
        }
