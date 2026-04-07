from hypothesis import given
from hypothesis import strategies as st

from wikify.aggregation.split import (
    aggregate_fact,
    all_session_facts,
    extract_facts_about_entity,
    extract_references_to_entity,
    reference_fact,
    session_facts_for_entity,
)
from wikify.models import (
    AggregatedFact,
    ExtractedEntity,
    Fact,
    Reference,
    ResolvedExtraction,
    SessionEntityFacts,
)


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
                ResolvedExtraction,
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
                ResolvedExtraction,
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
                ResolvedExtraction,
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
                ResolvedExtraction,
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


class TestSessionFactsForEntity:
    @given(st.builds(ResolvedExtraction), st.text())
    def test_entity_id_identity(self, extraction_result, entity_id):
        result: SessionEntityFacts = session_facts_for_entity(
            extraction_result, entity_id
        )

        assert result.entity_id == entity_id

    @given(st.data())
    def test_facts_extracted(self, data):
        entity_id = data.draw(st.text())
        relevant_facts = data.draw(
            st.lists(st.builds(Fact, subject_entity=st.just(entity_id)))
        )
        irrelevant_facts = data.draw(
            st.lists(st.builds(Fact).filter(lambda a: a.subject_entity != entity_id))
        )
        extraction = data.draw(
            st.builds(
                ResolvedExtraction,
                facts=st.permutations(relevant_facts + irrelevant_facts),
            )
        )

        result: SessionEntityFacts = session_facts_for_entity(extraction, entity_id)

        assert len(result.facts) == len(relevant_facts)

    @given(st.data())
    def test_references_extracted(self, data):
        entity_id = data.draw(st.text())
        relevant_facts = data.draw(
            st.lists(
                st.builds(
                    Fact,
                    object_entities=st.permutations(
                        [entity_id] + data.draw(st.lists(st.text()))
                    ),
                )
            )
        )
        irrelevant_facts = data.draw(
            st.lists(
                st.builds(Fact).filter(lambda a: entity_id not in a.object_entities)
            )
        )
        extraction = data.draw(
            st.builds(
                ResolvedExtraction,
                facts=st.permutations(relevant_facts + irrelevant_facts),
            )
        )

        result: SessionEntityFacts = session_facts_for_entity(extraction, entity_id)

        assert len(result.referenced_by) == len(relevant_facts)


class TestAllSessionFacts:
    @given(st.data())
    def test_includes_all_subject_entities(self, data):
        """All subject entities from facts should get a SessionEntityFacts."""
        facts = data.draw(st.lists(st.builds(Fact), min_size=1))
        extraction = data.draw(
            st.builds(ResolvedExtraction, facts=st.just(facts), entities=st.just([]))
        )

        result: list[SessionEntityFacts] = all_session_facts(extraction)

        subject_ids = {f.subject_entity for f in facts}
        result_ids = {sf.entity_id for sf in result}
        assert subject_ids <= result_ids

    @given(st.data())
    def test_includes_all_object_entities(self, data):
        """All object entities from facts should get a SessionEntityFacts."""
        facts = data.draw(st.lists(st.builds(Fact), min_size=1))
        extraction = data.draw(
            st.builds(ResolvedExtraction, facts=st.just(facts), entities=st.just([]))
        )

        result: list[SessionEntityFacts] = all_session_facts(extraction)

        object_ids = {eid for f in facts for eid in f.object_entities}
        result_ids = {sf.entity_id for sf in result}
        assert object_ids <= result_ids

    @given(st.data())
    def test_facts_cardinality(self, data):
        """The total facts across all SessionEntityFacts equals input facts count."""
        entity_ids = data.draw(st.lists(st.text(), min_size=1, unique=True))
        facts = data.draw(
            st.lists(
                st.builds(
                    Fact,
                    subject_entity=st.sampled_from(entity_ids),
                    object_entities=st.just([]),  # No object entities for simpler count
                )
            )
        )
        extraction = data.draw(
            st.builds(ResolvedExtraction, facts=st.just(facts), entities=st.just([]))
        )

        result: list[SessionEntityFacts] = all_session_facts(extraction)

        total_facts = sum(len(sf.facts) for sf in result)
        assert total_facts == len(facts)

    def test_empty_extraction(self):
        """An extraction with no facts should produce no SessionEntityFacts."""
        extraction = ResolvedExtraction(
            session_number=1,
            entities=[],
            facts=[],
        )

        result = all_session_facts(extraction)

        assert result == []
