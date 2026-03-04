"""Tests for terminal escape sequence filtering."""

from openhands.tools.terminal.utils.escape_filter import filter_terminal_queries


class TestFilterTerminalQueries:
    """Tests for filter_terminal_queries function."""

    def test_removes_dsr_query(self):
        """DSR (cursor position query) should be removed."""
        # ESC [ 6 n is the DSR query
        output = "before\x1b[6nafter"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_removes_multiple_dsr_queries(self):
        """Multiple DSR queries should all be removed."""
        output = "\x1b[6n\x1b[6ntext\x1b[6n"
        result = filter_terminal_queries(output)
        assert result == "text"

    def test_removes_osc_11_query_with_bel(self):
        """OSC 11 (background color query) with BEL terminator should be removed."""
        # ESC ] 11 ; ? BEL
        output = "before\x1b]11;?\x07after"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_removes_osc_11_query_with_st(self):
        """OSC 11 (background color query) with ST terminator should be removed."""
        # ESC ] 11 ; ? ESC \
        output = "before\x1b]11;?\x1b\\after"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_removes_osc_10_query(self):
        """OSC 10 (foreground color query) should be removed."""
        output = "before\x1b]10;?\x07after"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_removes_osc_4_query(self):
        """OSC 4 (palette color query) should be removed."""
        output = "before\x1b]4;0;?\x07after"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_removes_da_query(self):
        """DA (Device Attributes) primary query should be removed."""
        output = "before\x1b[cafter"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_removes_da_query_with_zero(self):
        """DA query with explicit 0 parameter should be removed."""
        output = "before\x1b[0cafter"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_removes_da2_query(self):
        """DA2 (Secondary Device Attributes) query should be removed."""
        output = "before\x1b[>cafter"
        result = filter_terminal_queries(output)
        assert result == "beforeafter"

    def test_preserves_color_codes(self):
        """ANSI color codes should be preserved."""
        # Red text: ESC [ 31 m
        output = "\x1b[31mred text\x1b[0m"
        result = filter_terminal_queries(output)
        assert result == "\x1b[31mred text\x1b[0m"

    def test_preserves_cursor_movement(self):
        """Cursor movement sequences should be preserved."""
        # Move cursor up: ESC [ A
        output = "line1\x1b[Aline2"
        result = filter_terminal_queries(output)
        assert result == "line1\x1b[Aline2"

    def test_preserves_bold_formatting(self):
        """Bold/bright formatting should be preserved."""
        output = "\x1b[1mbold\x1b[0m"
        result = filter_terminal_queries(output)
        assert result == "\x1b[1mbold\x1b[0m"

    def test_real_gh_output(self):
        """Test with actual captured gh command output pattern."""
        # This is a simplified version of what gh outputs
        output = (
            "\x1b]11;?\x1b\\\x1b[6n"  # Query sequences at start
            "\nShowing 3 of 183 open pull requests\n"
            "\x1b[0;32m#13199\x1b[0m  feat: feature  \x1b[0;36mbranch\x1b[0m"
        )
        result = filter_terminal_queries(output)
        # Query sequences removed, colors preserved
        assert "\x1b[6n" not in result
        assert "\x1b]11;?" not in result
        assert "\x1b[0;32m" in result  # Color preserved
        assert "Showing 3 of 183" in result

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert filter_terminal_queries("") == ""

    def test_no_escape_sequences(self):
        """Plain text without escape sequences should pass through unchanged."""
        output = "Hello, world!\nLine 2"
        assert filter_terminal_queries(output) == output

    def test_unicode_content(self):
        """Unicode content should be preserved."""
        output = "Hello 🌍\x1b[6n世界"
        result = filter_terminal_queries(output)
        assert result == "Hello 🌍世界"
