package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;

import java.io.StringReader;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ExtendedBufferedReader_7_4Test {
    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        extendedBufferedReader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
    }

    @Test
    void testGetLineNumber_initialValue() throws Exception {
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingLines() throws Exception {
        extendedBufferedReader.readLine();
        extendedBufferedReader.readLine();
        assertEquals(2, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterMultipleReads() throws Exception {
        extendedBufferedReader.readLine();
        extendedBufferedReader.readLine();
        extendedBufferedReader.readLine();
        assertEquals(3, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingNoLines() throws Exception {
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_boundaryAfterReadingLastLine() throws Exception {
        extendedBufferedReader.readLine();
        extendedBufferedReader.readLine();
        extendedBufferedReader.readLine();
        extendedBufferedReader.readLine();
        assertEquals(3, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReset() throws Exception {
        extendedBufferedReader.readLine();
        extendedBufferedReader.readLine();
        extendedBufferedReader = new ExtendedBufferedReader(new StringReader("Line 1\nLine 2\nLine 3"));
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_emptyReader() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        assertEquals(0, emptyReader.getLineNumber());
    }

    @Test
    void testGetLineNumber_afterReadingEmptyReader() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        emptyReader.readLine();
        assertEquals(0, emptyReader.getLineNumber());
    }

    @Test
    void testReadSingleCharacter() throws Exception {
        int result = extendedBufferedReader.read();
        assertEquals('L', result);
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testReadAgain() throws Exception {
        extendedBufferedReader.read();
        int result = extendedBufferedReader.readAgain();
        assertEquals('i', result);
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testReadCharArray() throws Exception {
        char[] buffer = new char[10];
        int length = extendedBufferedReader.read(buffer, 0, 10);
        assertEquals(10, length);
        assertArrayEquals(new char[] {'L', 'i', 'n', 'e', ' ', '1', '\n', 'L', 'i', 'n'}, buffer);
        assertEquals(1, extendedBufferedReader.getLineNumber());
    }

    @Test
    void testLookAhead() throws Exception {
        int result = extendedBufferedReader.lookAhead();
        assertEquals('L', result);
        assertEquals(0, extendedBufferedReader.getLineNumber());
    }
}