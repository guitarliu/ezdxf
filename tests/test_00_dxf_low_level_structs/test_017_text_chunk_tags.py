# Created: 02.05.2014
# Copyright (c) 2014-2019, Manfred Moitzi
# License: MIT License
from ezdxf.modern.solid3d import convert_tags_to_text_lines, convert_text_lines_to_tags, DXFTag


class TestTextChunkConverter:
    def test_text_lines_to_tags_short_lines(self):
        text = ["123", "456", "789"]
        result = list(convert_text_lines_to_tags(text))
        assert result[0] == (1, "123")
        assert result[1] == (1, "456")
        assert result[2] == (1, "789")

    def test_text_lines_to_tags_long_lines(self):
        line = "0123456789" * 30
        text = [line, line]
        result = list(convert_text_lines_to_tags(text))
        assert 4 == len(result)
        assert result[0] == (1, line[:255])
        assert result[1] == (3, line[255:])
        assert result[2] == (1, line[:255])
        assert result[3] == (3, line[255:])

    def test_text_lines_to_tags_empty_list(self):
        result = list(convert_text_lines_to_tags([]))
        assert len(result) == 0

    def test_tags_to_text_lines_short_lines(self):
        tags = [
            DXFTag(1, "123"),
            DXFTag(1, "456"),
            DXFTag(1, "789")
        ]
        expected = ["123", "456", "789"]
        assert expected == list(convert_tags_to_text_lines(tags))

    def test_tags_to_text_lines_long_lines(self):
        line = "0123456789" * 30
        tags = [
            DXFTag(1, line[:255]),
            DXFTag(3, line[255:]),
            DXFTag(1, line[:255]),
            DXFTag(3, line[255:]),
        ]
        expected = [line, line]
        assert expected == list(convert_tags_to_text_lines(tags))

    def test_tags_to_text_lines_empty_list(self):
        result = list(convert_tags_to_text_lines([]))
        assert len(result) == 0