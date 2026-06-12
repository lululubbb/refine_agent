package org.apache.commons.csv;

import java.io.BufferedReader;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ExtendedBufferedReader_2_2Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        String input = "Line 1\nLine 2\rLine 3\n";
        Reader stringReader = new StringReader(input);
        reader = new ExtendedBufferedReader(stringReader);
    }

    @Test
    void testRead_normalCase() throws Exception {
        assertEquals('L', reader.read());
        assertEquals('i', reader.read());
        assertEquals('n', reader.read());
        assertEquals('e', reader.read());
        assertEquals(' ', reader.read());
        assertEquals('1', reader.read());
        assertEquals('\n', reader.read());
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        reader.read(); // Read until the end of Line 1
        reader.read(); // Read Line break
        assertEquals('L', reader.read()); // Start of Line 2
        assertEquals('i', reader.read());
        assertEquals('n', reader.read());
        assertEquals('e', reader.read());
        assertEquals(' ', reader.read());
        assertEquals('2', reader.read());
        assertEquals('\r', reader.read());
        assertEquals('L', reader.read()); // Start of Line 3
        assertEquals('i', reader.read()); // Read 'i'
        assertEquals('n', reader.read()); // Read 'n'
        assertEquals('e', reader.read()); // Read 'e'
        assertEquals(' ', reader.read()); // Read ' '
        assertEquals('3', reader.read()); // Read '3'
        assertEquals('\n', reader.read()); // Read end of Line 3
    }

    @Test
    void testRead_endOfStream() throws Exception {
        while (reader.read() != ExtendedBufferedReader.END_OF_STREAM) {
            // Read until end of stream
        }
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, reader.read());
    }

    @Test
    void testRead_invalidCharacter() throws Exception {
        Reader stringReader = new StringReader("\r\n");
        reader = new ExtendedBufferedReader(stringReader);
        assertEquals('\r', reader.read());
        assertEquals('\n', reader.read());
    }
}