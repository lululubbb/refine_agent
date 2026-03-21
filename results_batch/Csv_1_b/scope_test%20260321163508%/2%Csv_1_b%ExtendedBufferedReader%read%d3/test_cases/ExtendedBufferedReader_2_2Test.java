package org.apache.commons.csv;
import java.io.BufferedReader;
import org.apache.commons.csv.ExtendedBufferedReader;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

import static org.junit.jupiter.api.Assertions.*;

class ExtendedBufferedReader_2_2Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        // Initialize with a simple Reader, will be overridden in specific tests when needed
        reader = new ExtendedBufferedReader(new StringReader(""));
    }

    @Test
    void testRead_normalPath_readsCharactersAndCountsLines() throws IOException {
        String input = "a\nb\nc";
        reader = new ExtendedBufferedReader(new StringReader(input));

        int countNewLines = 0;
        int ch;
        int totalChars = input.length();
        for (int i = 0; i < totalChars; i++) {
            ch = reader.read();
            if (ch == '\n') {
                countNewLines++;
            }
            assertEquals(ch, reader.lastChar, "lastChar should be updated to current char");
        }
        // The lineCounter field should equal the number of '\n' characters read
        assertEquals(countNewLines, getLineCounter(reader));
    }

    @Test
    void testRead_emptyInput_returnsEndOfStream() throws IOException {
        reader = new ExtendedBufferedReader(new StringReader(""));
        int ch = reader.read();
        assertEquals(-1, ch, "Empty input should return END_OF_STREAM (-1)");
        assertEquals(ch, reader.lastChar, "lastChar should be updated to -1 on EOF");
        assertEquals(0, getLineCounter(reader), "lineCounter should be 0 on empty input");
    }

    @Test
    void testRead_onlyNewLineInInput_incrementsLineCounter() throws IOException {
        reader = new ExtendedBufferedReader(new StringReader("\n"));
        int ch = reader.read();
        assertEquals('\n', ch, "Should read newline character");
        assertEquals(ch, reader.lastChar, "lastChar should be newline");
        assertEquals(1, getLineCounter(reader), "lineCounter should increment once for newline");
        int eof = reader.read();
        assertEquals(-1, eof, "Next read should return EOF");
    }

    @Test
    void testRead_multipleSequentialNewLines_incrementsLineCounterCorrectly() throws IOException {
        String input = "\n\n\n";
        reader = new ExtendedBufferedReader(new StringReader(input));
        int countNewLines = 0;
        int ch;
        for (int i = 0; i < input.length(); i++) {
            ch = reader.read();
            assertEquals('\n', ch, "Should read newline character");
            countNewLines++;
            assertEquals(countNewLines, getLineCounter(reader), "lineCounter should match newlines read");
        }
        int eof = reader.read();
        assertEquals(-1, eof, "Next read should return EOF");
        assertEquals(countNewLines, getLineCounter(reader));
    }

    @Test
    void testRead_throwsIOExceptionOnClosedReader() throws IOException {
        Reader r = new StringReader("abc");
        reader = new ExtendedBufferedReader(r);
        r.close();
        IOException thrown = assertThrows(IOException.class, () -> reader.read());
        assertNotNull(thrown, "read() should throw IOException when underlying reader is closed");
    }

    // Helper method to get private field lineCounter via reflection
    private int getLineCounter(ExtendedBufferedReader r) {
        try {
            var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
            field.setAccessible(true);
            return field.getInt(r);
        } catch (ReflectiveOperationException e) {
            fail("Reflection error accessing lineCounter: " + e.getMessage());
            return -1;
        }
    }
}