import copy
import pytest
from local_asr.artifacts import make_cues


def test_observed_last_word_boundary_is_clipped_and_audited():
    words = [{"text": "末尾文字", "start": 31.36, "end": 31.52}]
    original = copy.deepcopy(words)
    corrections = []
    # Exercise the existing three-argument production call before audit metadata.
    assert make_cues(words, 1935.5, 31.5)[-1]["end"] == 1967.0
    cues = make_cues(words, 1935.5, 31.5, corrections=corrections)
    assert cues == [{"start": 1966.86, "end": 1967.0, "text": "末尾文字"}]
    assert words == original
    assert corrections == [{"word_index": 0, "original_start": 31.36, "original_end": 31.52,
                            "corrected_end": 31.5, "reason": "end_boundary_tolerance"}]


@pytest.mark.parametrize("words", [
    [{"text":"错误", "start":31.36, "end":31.521}],
    [{"text":"错误", "start":31.5, "end":31.51}],
    [{"text":"错误", "start":-0.01, "end":0.1}],
    [{"text":"错误", "start":1.0, "end":0.9}],
    [{"text":"错误", "start":0, "end":float('nan')}],
    [{"text":"前", "start":1.0, "end":2.0}, {"text":"后", "start":0.9, "end":1.1}],
])
def test_invalid_alignment_is_not_silently_accepted(words):
    with pytest.raises(ValueError, match="Invalid or unordered"):
        make_cues(words, 0, 31.5)


def test_valid_and_zero_duration_words_keep_text():
    corrections = []
    cues = make_cues([{"text":"正常", "start":0, "end":1}, {"text":"尾字", "start":1, "end":1}], 10, 2, corrections=corrections)
    assert cues == [{"start":10, "end":11, "text":"正常尾字"}]
    assert corrections == []
    assert make_cues([], 0, 2) == []
