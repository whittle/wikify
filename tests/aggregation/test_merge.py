from hypothesis import given
from hypothesis import strategies as st

from wikify.aggregation.merge import merge_session_facts
from wikify.models.entity import (
    AggregatedFact,
    Entity,
    EntityData,
    Reference,
    SessionEntityFacts,
)


class TestMergeSessionFacts:
    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_entity_id_identity(self, entity_id, entity, session_facts):
        """The output entity_id matches the input entity_id."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        assert result.entity_id == entity_id

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_canonical_name_from_entity(self, entity_id, entity, session_facts):
        """canonical_name comes from the Entity parameter."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        assert result.canonical_name == entity.canonical_name

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_aliases_from_entity(self, entity_id, entity, session_facts):
        """aliases come from the Entity parameter."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        assert result.aliases == entity.aliases

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_type_from_entity(self, entity_id, entity, session_facts):
        """type comes from the Entity parameter."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        assert result.type == entity.type

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_first_appearance_from_entity(self, entity_id, entity, session_facts):
        """first_appearance comes from the Entity parameter."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        assert result.first_appearance == entity.first_appearance

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_all_facts_collected(self, entity_id, entity, session_facts):
        """All facts from all SessionEntityFacts appear in output."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        expected_facts = [f for sf in session_facts for f in sf.facts]
        assert result.facts == expected_facts

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_all_references_collected(self, entity_id, entity, session_facts):
        """All references from all SessionEntityFacts appear in output."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        expected_refs = [r for sf in session_facts for r in sf.referenced_by]
        assert result.referenced_by == expected_refs

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_sessions_derived_from_facts_and_refs(
        self, entity_id, entity, session_facts
    ):
        """sessions_appeared contains exactly the unique source_session values."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        expected_sessions = {f.source_session for sf in session_facts for f in sf.facts}
        expected_sessions |= {
            r.source_session for sf in session_facts for r in sf.referenced_by
        }
        assert set(result.sessions_appeared) == expected_sessions

    @given(st.text(), st.builds(Entity), st.lists(st.builds(SessionEntityFacts)))
    def test_sessions_sorted(self, entity_id, entity, session_facts):
        """sessions_appeared is sorted in ascending order."""
        result: EntityData = merge_session_facts(entity_id, entity, session_facts)

        assert result.sessions_appeared == sorted(result.sessions_appeared)

    @given(st.text(), st.builds(Entity))
    def test_empty_session_facts(self, entity_id, entity):
        """Empty session_facts list produces empty facts, refs, and sessions."""
        result: EntityData = merge_session_facts(entity_id, entity, [])

        assert result.facts == []
        assert result.referenced_by == []
        assert result.sessions_appeared == []

    @given(st.data())
    def test_facts_order_preserved_within_session(self, data):
        """Facts within each SessionEntityFacts preserve their order."""
        entity_id = data.draw(st.text())
        entity = data.draw(st.builds(Entity))
        facts1 = data.draw(st.lists(st.builds(AggregatedFact), min_size=1))
        facts2 = data.draw(st.lists(st.builds(AggregatedFact), min_size=1))
        sf1 = SessionEntityFacts(entity_id=entity_id, facts=facts1, referenced_by=[])
        sf2 = SessionEntityFacts(entity_id=entity_id, facts=facts2, referenced_by=[])

        result: EntityData = merge_session_facts(entity_id, entity, [sf1, sf2])

        # Facts from sf1 should appear before facts from sf2
        assert result.facts == facts1 + facts2

    @given(st.data())
    def test_references_order_preserved_within_session(self, data):
        """References within each SessionEntityFacts preserve their order."""
        entity_id = data.draw(st.text())
        entity = data.draw(st.builds(Entity))
        refs1 = data.draw(st.lists(st.builds(Reference), min_size=1))
        refs2 = data.draw(st.lists(st.builds(Reference), min_size=1))
        sf1 = SessionEntityFacts(entity_id=entity_id, facts=[], referenced_by=refs1)
        sf2 = SessionEntityFacts(entity_id=entity_id, facts=[], referenced_by=refs2)

        result: EntityData = merge_session_facts(entity_id, entity, [sf1, sf2])

        # Refs from sf1 should appear before refs from sf2
        assert result.referenced_by == refs1 + refs2
