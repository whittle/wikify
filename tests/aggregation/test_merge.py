from hypothesis import assume, given
from hypothesis import strategies as st

from wikify.aggregation.errors import EntityDataMergeIncompatibility
from wikify.aggregation.merge import merge_entity_data
from wikify.models.entity import AggregatedFact, EntityData, Reference
from wikify.models.fact import ConfidenceLevel


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
        """If there's only one element to merge, return it unchanged."""
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
