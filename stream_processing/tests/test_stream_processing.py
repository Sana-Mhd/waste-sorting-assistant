"""The four concepts of Hometask 2 and the two pipeline goals."""
import inspect

import pytest

from stream_processing import (
    BoundingBox,
    ConfidenceFilter,
    MaterialMapper,
    Pipeline,
    RouteAssigner,
    SorterEvent,
    SorterStream,
    StreamProcessor,
    simulate_payloads,
)


def event(confidence=0.9, tags=("bottle", "transparent"), width=100, height=100) -> SorterEvent:
    return SorterEvent("item-1", confidence, BoundingBox(0, 0, width, height), tags)


def payload(**changes) -> dict:
    message = {
        "item_id": "item-1",
        "confidence": 0.9,
        "box": {"x": 0, "y": 0, "width": 100, "height": 100},
        "tags": ["can", "metallic"],
    }
    return {**message, **changes}


# --- abstract base class ------------------------------------------------------

def test_stream_processor_is_abstract():
    assert inspect.isabstract(StreamProcessor)
    with pytest.raises(TypeError):
        StreamProcessor()


def test_processor_without_process_cannot_be_created():
    class Incomplete(StreamProcessor):
        pass

    with pytest.raises(TypeError):
        Incomplete()


# --- inheritance and polymorphism ---------------------------------------------

@pytest.mark.parametrize(
    "processor",
    [ConfidenceFilter(), MaterialMapper(), Pipeline(MaterialMapper(), RouteAssigner())],
)
def test_every_processor_has_the_same_api(processor):
    assert isinstance(processor, StreamProcessor)
    assert list(processor.process([event()]))[0].item_id == "item-1"


def test_a_new_processor_works_in_a_pipeline_without_other_changes():
    class OnlyLarge(StreamProcessor):
        def process(self, stream):
            return (item for item in stream if item.box.area >= 10_000)

    pipeline = OnlyLarge() | MaterialMapper()
    assert [item.material for item in pipeline.process([event(width=10, height=10), event()])] == ["PET"]


# --- operator overloading -----------------------------------------------------

def test_or_builds_a_pipeline_that_runs_in_order():
    first, second = ConfidenceFilter(), MaterialMapper()
    pipeline = first | second
    assert isinstance(pipeline, Pipeline)
    assert pipeline.steps == (first, second)


def test_three_steps_can_be_chained():
    pipeline = ConfidenceFilter(0.5) | MaterialMapper() | RouteAssigner()
    assert [item.routing_code for item in pipeline.process([event()])] == ["A1-M"]


def test_or_with_something_else_is_a_type_error():
    with pytest.raises(TypeError):
        ConfidenceFilter() | "not a processor"


def test_empty_pipeline_is_refused():
    with pytest.raises(ValueError):
        Pipeline()


# --- iterators and generators -------------------------------------------------

def test_stream_is_its_own_iterator():
    stream = SorterStream([payload()])
    assert iter(stream) is stream
    assert next(stream).item_id == "item-1"
    with pytest.raises(StopIteration):
        next(stream)


def test_stream_skips_broken_messages_and_counts_them():
    broken = [{"item_id": "no data"}, payload(box={"x": 0, "y": 0, "width": 0, "height": 5}), payload(confidence="?")]
    stream = SorterStream([*broken, payload(item_id="good")])

    assert [item.item_id for item in stream] == ["good"]
    assert stream.skipped == 3


def test_simulated_sorter_is_a_generator():
    assert inspect.isgenerator(simulate_payloads(3))
    assert len(list(simulate_payloads(3))) == 3


def test_same_seed_gives_the_same_messages():
    assert list(simulate_payloads(5, seed=1)) == list(simulate_payloads(5, seed=1))


def test_processing_is_lazy_one_item_at_a_time():
    read = []

    def source():
        for number in range(3):
            read.append(number)
            yield event()

    results = (ConfidenceFilter() | MaterialMapper()).process(source())

    assert read == []                   # nothing happens until an item is asked for
    next(results)
    assert read == [0]                  # one item in, one item out


# --- goal 1: filter low-confidence predictions --------------------------------

def test_filter_keeps_only_confident_events():
    events = [event(0.59), event(0.6), event(0.95)]
    assert [item.confidence for item in ConfidenceFilter(0.6).process(events)] == [0.6, 0.95]


def test_filter_refuses_a_threshold_out_of_range():
    with pytest.raises(ValueError):
        ConfidenceFilter(1.5)


# --- goal 2: tags and box into material and routing code ----------------------

@pytest.mark.parametrize(
    "tags, material",
    [
        (("bottle", "transparent"), "PET"),
        (("opaque", "bottle"), "HDPE"),
        (("can", "metallic", "dented"), "Aluminum"),
        (("box", "brown"), "Other"),
    ],
)
def test_tags_become_a_material(tags, material):
    assert next(MaterialMapper().process([event(tags=tags)])).material == material


@pytest.mark.parametrize(
    "tags, width, height, code",
    [
        (("bottle", "transparent"), 50, 50, "A1-S"),        # 2 500 pixels
        (("bottle", "opaque"), 100, 100, "A2-M"),           # 10 000 pixels
        (("can", "metallic"), 200, 200, "B1-L"),            # 40 000 pixels
        (("box", "brown"), 100, 100, "RJ-M"),               # no material: reject lane
    ],
)
def test_material_and_box_become_a_routing_code(tags, width, height, code):
    pipeline = MaterialMapper() | RouteAssigner()
    assert next(pipeline.process([event(tags=tags, width=width, height=height)])).routing_code == code


def test_route_needs_a_material_first():
    with pytest.raises(ValueError, match="MaterialMapper"):
        next(RouteAssigner().process([event()]))


def test_processors_do_not_change_the_original_event():
    original = event()
    next(MaterialMapper().process([original]))
    assert original.material is None


# --- everything together ------------------------------------------------------

def test_whole_pipeline_on_the_simulated_sorter():
    stream = SorterStream(simulate_payloads(200))
    pipeline = ConfidenceFilter(0.6) | MaterialMapper() | RouteAssigner()

    items = list(pipeline.process(stream))

    assert 0 < len(items) < 200
    assert all(item.confidence >= 0.6 for item in items)
    assert {item.material for item in items} == {"PET", "HDPE", "Aluminum", "Other"}
    assert all(item.routing_code for item in items)
